import sys
import os
import json
from datetime import datetime
import pandas as pd
import numpy as np
from flask import Flask, render_template_string, jsonify, request, Response

from scanner import run_stock_scan
from data_fetcher import fetch_stock_ohlcv
from technical_indicators import calculate_rsi, calculate_bollinger_bands

app = Flask(__name__)

# 스캔 데이터 세션 저장소
scan_cache = {"data": []}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>📈 바닥 반등 주식찾기 Mobile</title>
    <!-- PWA & Mobile Web App Meta -->
    <meta name="theme-color" content="#1E3A8A">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <link rel="apple-touch-icon" href="https://img.icons8.com/color/96/line-chart.png">
    
    <!-- Bootstrap 5 & FontAwesome -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>

    <style>
        body {
            background-color: #F8FAFC;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            padding-bottom: 30px;
        }
        .header-bg {
            background: linear-gradient(135deg, #1E3A8A 0%, #3B82F6 100%);
            color: white;
            padding: 20px 16px;
            border-radius: 0 0 16px 16px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.12);
        }
        .preset-pill {
            border-radius: 20px;
            font-size: 0.82rem;
            font-weight: 700;
            padding: 8px 12px;
            white-space: nowrap;
        }
        .stock-card {
            background: white;
            border-radius: 12px;
            border: 1px solid #E2E8F0;
            padding: 14px;
            margin-bottom: 12px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.04);
            transition: transform 0.15s ease;
        }
        .stock-card:active {
            transform: scale(0.98);
        }
        .badge-score-high {
            background-color: #DCFCE7;
            color: #15803D;
            font-weight: 800;
            font-size: 0.85rem;
            padding: 4px 10px;
            border-radius: 20px;
        }
        .badge-score-mid {
            background-color: #FEF9C3;
            color: #A16207;
            font-weight: 800;
            font-size: 0.85rem;
            padding: 4px 10px;
            border-radius: 20px;
        }
        .metric-box {
            background-color: #F8FAFC;
            border-radius: 8px;
            padding: 8px;
            text-align: center;
        }
        .metric-lbl {
            font-size: 0.72rem;
            color: #64748B;
        }
        .metric-val {
            font-size: 0.88rem;
            font-weight: 700;
            color: #0F172A;
        }
        .btn-naver {
            background-color: #03C75A;
            color: white !important;
            font-weight: bold;
            border-radius: 8px;
            padding: 10px;
            text-decoration: none;
            display: block;
            text-align: center;
        }
    </style>
</head>
<body>

    <!-- 모바일 상단 헤더 -->
    <div class="header-bg mb-3">
        <div class="d-flex justify-content-between align-items-center">
            <div>
                <h5 class="fw-bold mb-1"><i class="fa-solid fa-chart-line me-2"></i>네이버 증권 바닥 반등 발굴기</h5>
                <small class="text-white-50">52주 최저가 + 외인/기관 수급 + 거래량 폭증 분석</small>
            </div>
        </div>
    </div>

    <div class="container px-3">
        
        <!-- 프리셋 바 -->
        <div class="d-flex gap-2 overflow-x-auto pb-2 mb-3">
            <button class="btn btn-warning text-dark preset-pill" onclick="applyPreset('DOUBLE')">🔥 외인+기관 쌍끌이</button>
            <button class="btn btn-primary preset-pill" onclick="applyPreset('VOL')">💥 거래량 폭증</button>
            <button class="btn btn-success preset-pill" onclick="applyPreset('PBR')">🛡️ PBR 저평가</button>
            <button class="btn btn-danger preset-pill" onclick="applyPreset('RSI')">⚡ RSI 과매도</button>
        </div>

        <!-- 스캔 컨트롤 카드 -->
        <div class="card border-0 shadow-sm rounded-3 mb-3">
            <div class="card-body p-3">
                <div class="row g-2">
                    <div class="col-6">
                        <label class="form-label small fw-bold">시장 선택</label>
                        <select id="marketSelect" class="form-select form-select-sm">
                            <option value="ALL">전체 (KOSPI+KOSDAQ)</option>
                            <option value="KOSPI">코스피 (KOSPI)</option>
                            <option value="KOSDAQ">코스닥 (KOSDAQ)</option>
                        </select>
                    </div>
                    <div class="col-6">
                        <label class="form-label small fw-bold">시총 상위 스캔 수</label>
                        <select id="topNSelect" class="form-select form-select-sm">
                            <option value="50">50개 종목 (빠름)</option>
                            <option value="100" selected>100개 종목 (추천)</option>
                            <option value="200">200개 종목</option>
                        </select>
                    </div>
                </div>

                <div class="mt-3">
                    <button id="btnScan" class="btn btn-primary w-100 fw-bold py-2" onclick="startScan()">
                        <i class="fa-solid fa-rocket me-2"></i>바닥 반등 종목 스캔 시작
                    </button>
                </div>
            </div>
        </div>

        <!-- 로딩 상태 -->
        <div id="loadingBox" class="text-center py-4 d-none">
            <div class="spinner-border text-primary" role="status"></div>
            <div class="mt-2 fw-bold text-primary" id="statusText">종목 수집 및 반등 분석 중...</div>
        </div>

        <!-- 결과 요약 메트릭 -->
        <div id="summaryCards" class="row g-2 mb-3 d-none">
            <div class="col-6">
                <div class="card border-0 shadow-sm bg-white p-2 text-center">
                    <small class="text-muted">발굴된 종목 수</small>
                    <div id="cntTotal" class="h5 fw-bold text-primary mb-0">0 개</div>
                </div>
            </div>
            <div class="col-6">
                <div class="card border-0 shadow-sm bg-white p-2 text-center">
                    <small class="text-muted">강력 반등 (70점+)</small>
                    <div id="cntHigh" class="h5 fw-bold text-success mb-0">0 개</div>
                </div>
            </div>
        </div>

        <!-- 종목 리스트 Container -->
        <div id="stockList"></div>

        <!-- PWA 홈 화면 추가 안내 -->
        <div class="card border-0 bg-light p-3 text-secondary small rounded-3 mt-4">
            <div class="fw-bold text-primary mb-1"><i class="fa-solid fa-mobile-screen-button me-1"></i>스마트폰 홈 화면에 앱으로 설치하는 방법</div>
            <div>• <b>Android (Chrome)</b>: 상단 메뉴 [⋮] → [홈 화면에 추가]</div>
            <div>• <b>iPhone (Safari)</b>: 하단 공유 [공유] → [홈 화면에 추가]</div>
        </div>

    </div>

    <script>
        let allStockData = [];

        function applyPreset(type) {
            if (!allStockData.length) {
                alert("먼저 [스캔 시작] 버튼을 눌러 스캔을 진행해 주세요.");
                return;
            }
            let filtered = allStockData;
            if (type === 'DOUBLE') {
                filtered = allStockData.filter(d => d.foreign_buy_3d > 0 && d.organ_buy_3d > 0);
            } else if (type === 'VOL') {
                filtered = allStockData.filter(d => d.vol_surge_ratio >= 1.5);
            } else if (type === 'PBR') {
                filtered = allStockData.filter(d => d.pbr && d.pbr <= 1.0);
            } else if (type === 'RSI') {
                filtered = allStockData.filter(d => d.rsi <= 35);
            }
            renderStockList(filtered);
        }

        async function startScan() {
            const market = document.getElementById("marketSelect").value;
            const topN = document.getElementById("topNSelect").value;

            document.getElementById("btnScan").disabled = true;
            document.getElementById("loadingBox").classList.remove("d-none");
            document.getElementById("stockList").innerHTML = "";
            document.getElementById("summaryCards").classList.add("d-none");

            try {
                const res = await fetch(`/api/scan?market=${market}&top_n=${topN}`);
                const data = await res.json();
                allStockData = data;

                document.getElementById("loadingBox").classList.add("d-none");
                document.getElementById("btnScan").disabled = false;

                if (data.length > 0) {
                    document.getElementById("summaryCards").classList.remove("d-none");
                    document.getElementById("cntTotal").innerText = `${data.length} 개`;
                    const highCnt = data.filter(d => d.total_score >= 70).length;
                    document.getElementById("cntHigh").innerText = `${highCnt} 개`;
                    renderStockList(data);
                } else {
                    document.getElementById("stockList").innerHTML = `<div class="alert alert-warning text-center">조건에 맞는 반등 유망 종목이 없습니다.</div>`;
                }
            } catch (err) {
                document.getElementById("loadingBox").classList.add("d-none");
                document.getElementById("btnScan").disabled = false;
                alert("스캔 중 오류가 발생하였습니다: " + err);
            }
        }

        function renderStockList(items) {
            const container = document.getElementById("stockList");
            if (!items.length) {
                container.innerHTML = `<div class="alert alert-warning text-center">선택한 프리셋에 해당하는 종목이 없습니다.</div>`;
                return;
            }

            let html = "";
            items.forEach((item, idx) => {
                const badgeClass = item.total_score >= 70 ? 'badge-score-high' : 'badge-score-mid';
                const reasons = item.reasons.map(r => `<li>${r}</li>`).join('');

                html += `
                <div class="stock-card">
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <div>
                            <span class="fw-bold fs-6">${item.name}</span>
                            <small class="text-muted">(${item.code}) • ${item.market}</small>
                        </div>
                        <span class="${badgeClass}">${item.total_score}점 [${item.grade}]</span>
                    </div>

                    <div class="row g-1 mb-2">
                        <div class="col-6">
                            <div class="metric-box">
                                <div class="metric-lbl">현재가</div>
                                <div class="metric-val text-danger">${item.current_price.toLocaleString()}원</div>
                            </div>
                        </div>
                        <div class="col-6">
                            <div class="metric-box">
                                <div class="metric-lbl">52주최저 이격률</div>
                                <div class="metric-val">+${item.diff_from_52w_low_pct.toFixed(1)}%</div>
                            </div>
                        </div>
                        <div class="col-6 mt-1">
                            <div class="metric-box">
                                <div class="metric-lbl">외인 3일 순매수</div>
                                <div class="metric-val text-success">${item.foreign_buy_3d > 0 ? '+' : ''}${item.foreign_buy_3d.toLocaleString()}주</div>
                            </div>
                        </div>
                        <div class="col-6 mt-1">
                            <div class="metric-box">
                                <div class="metric-lbl">기관 3일 순매수</div>
                                <div class="metric-val text-success">${item.organ_buy_3d > 0 ? '+' : ''}${item.organ_buy_3d.toLocaleString()}주</div>
                            </div>
                        </div>
                    </div>

                    <button class="btn btn-outline-primary btn-sm w-100 mt-2 fw-bold" type="button" data-bs-toggle="collapse" data-bs-target="#detail-${idx}">
                        🔍 상세 분석 및 차트 보기
                    </button>

                    <div class="collapse mt-3" id="detail-${idx}">
                        <div class="card card-body bg-light border-0 p-3">
                            <h6 class="fw-bold text-dark mb-2">💡 핵심 반등 사유</h6>
                            <ul class="small text-secondary ps-3 mb-3">${reasons}</ul>

                            <h6 class="fw-bold text-dark mb-2">📊 수급 및 밸류에이션</h6>
                            <div class="small mb-3">
                                <div>• <b>PBR</b>: ${item.pbr ? item.pbr.toFixed(2) + '배' : '-'} | <b>PER</b>: ${item.per ? item.per.toFixed(1) + '배' : '-'}</div>
                                <div>• <b>거래량 급증률</b>: ${item.vol_surge_ratio.toFixed(2)}배 | <b>RSI(14)</b>: ${item.rsi.toFixed(1)}</div>
                            </div>

                            <a href="${item.naver_link}" target="_blank" class="btn-naver mb-3">
                                <i class="fa-solid fa-arrow-up-right-from-square me-1"></i>네이버 증권 모바일 연결
                            </a>

                            <div id="chart-container-${item.code}" style="height: 350px;"></div>
                            <button class="btn btn-sm btn-secondary w-100 mt-2" onclick="loadChart('${item.code}', 'chart-container-${item.code}')">
                                📊 터치 차트 불러오기
                            </button>
                        </div>
                    </div>
                </div>
                `;
            });
            container.innerHTML = html;
        }

        async function loadChart(code, containerId) {
            const container = document.getElementById(containerId);
            container.innerHTML = `<div class="text-center py-4"><div class="spinner-border text-primary spinner-border-sm"></div> 차트 생성중...</div>`;

            try {
                const res = await fetch(`/api/chart/${code}`);
                const data = await res.json();
                if (data.error) {
                    container.innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
                    return;
                }
                Plotly.newPlot(containerId, data.data, data.layout, {responsive: true, displayModeBar: false});
            } catch (err) {
                container.innerHTML = `<div class="alert alert-danger">차트 로딩 실패: ${err}</div>`;
            }
        }
    </script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/scan')
def api_scan():
    market = request.args.get('market', 'ALL')
    top_n = int(request.args.get('top_n', 100))
    df_res = run_stock_scan(market=market, top_n=top_n)
    if df_res is None or df_res.empty:
        scan_cache["data"] = []
        return jsonify([])
    
    records = df_res.to_dict(orient='records')
    scan_cache["data"] = records
    return jsonify(records)

@app.route('/api/chart/<code>')
def api_chart(code):
    df_chart = fetch_stock_ohlcv(code, days=90)
    if df_chart is None or len(df_chart) == 0:
        return jsonify({"error": "차트 데이터를 불러올 수 없습니다."})

    df_chart['MA5'] = df_chart['Close'].rolling(5).mean()
    df_chart['MA20'] = df_chart['Close'].rolling(20).mean()
    df_chart['RSI'] = calculate_rsi(df_chart['Close'], 14)
    upper, mid, lower, _ = calculate_bollinger_bands(df_chart['Close'], 20, 2.0)
    df_chart['BB_Lower'] = lower

    dates = df_chart.index.strftime('%Y-%m-%d').tolist()

    data = [
        {
            "type": "candlestick",
            "x": dates,
            "open": df_chart['Open'].tolist(),
            "high": df_chart['High'].tolist(),
            "low": df_chart['Low'].tolist(),
            "close": df_chart['Close'].tolist(),
            "increasing": {"line": {"color": "#EF4444"}},
            "decreasing": {"line": {"color": "#3B82F6"}},
            "name": "주가"
        },
        {
            "type": "scatter",
            "mode": "lines",
            "x": dates,
            "y": df_chart['MA5'].tolist(),
            "line": {"color": "orange", "width": 1},
            "name": "5일선"
        },
        {
            "type": "scatter",
            "mode": "lines",
            "x": dates,
            "y": df_chart['MA20'].tolist(),
            "line": {"color": "green", "width": 1.5},
            "name": "20일선"
        }
    ]

    layout = {
        "margin": {"l": 20, "r": 20, "t": 20, "b": 20},
        "showlegend": False,
        "xaxis": {"rangeslider": {"visible": False}},
        "yaxis": {"autorange": True}
    }

    return jsonify({"data": data, "layout": layout})

if __name__ == "__main__":
    print("Starting Mobile App Server on http://0.0.0.0:5000 ...")
    app.run(host="0.0.0.0", port=5000, debug=False)
