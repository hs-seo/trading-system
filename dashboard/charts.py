"""
Chart Components - 기술적 분석 차트 컴포넌트
"""
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import List, Optional, Dict, Any


def create_candlestick_chart(
    df: pd.DataFrame,
    symbol: str = "",
    show_ma: List[int] = [20, 50, 200],
    show_bb: bool = True,
    show_volume: bool = True,
    show_macd: bool = False,
    show_rsi: bool = False,
    height: int = 600,
) -> go.Figure:
    """
    캔들스틱 차트 생성

    Args:
        df: OHLCV + 지표 DataFrame
        symbol: 종목 심볼
        show_ma: 표시할 이동평균선 기간 리스트
        show_bb: 볼린저 밴드 표시
        show_volume: 거래량 표시
        show_macd: MACD 표시
        show_rsi: RSI 표시
        height: 차트 높이
    """
    # 서브플롯 구성 계산
    n_rows = 1
    row_heights = [0.7]
    subplot_titles = [symbol or "Price"]

    if show_volume:
        n_rows += 1
        row_heights.append(0.15)
        subplot_titles.append("Volume")

    if show_macd:
        n_rows += 1
        row_heights.append(0.15)
        subplot_titles.append("MACD")

    if show_rsi:
        n_rows += 1
        row_heights.append(0.15)
        subplot_titles.append("RSI")

    # 높이 정규화
    total = sum(row_heights)
    row_heights = [h/total for h in row_heights]

    fig = make_subplots(
        rows=n_rows, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=row_heights,
        subplot_titles=subplot_titles,
    )

    # x축 데이터
    x_data = df['timestamp'] if 'timestamp' in df.columns else df.index

    # 1. 캔들스틱
    fig.add_trace(
        go.Candlestick(
            x=x_data,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='OHLC',
            increasing_line_color='#26a69a',
            decreasing_line_color='#ef5350',
        ),
        row=1, col=1
    )

    # 이동평균선
    ma_colors = {5: '#ff9800', 10: '#ff5722', 20: '#2196f3', 50: '#9c27b0', 100: '#607d8b', 150: '#795548', 200: '#f44336'}
    for period in show_ma:
        col_name = f'ma{period}'
        if col_name in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=x_data, y=df[col_name],
                    name=f'MA{period}',
                    line=dict(color=ma_colors.get(period, 'gray'), width=1),
                ),
                row=1, col=1
            )

    # 볼린저 밴드
    if show_bb and 'bb_upper' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=x_data, y=df['bb_upper'],
                name='BB Upper',
                line=dict(color='rgba(128,128,128,0.5)', width=1),
            ),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(
                x=x_data, y=df['bb_lower'],
                name='BB Lower',
                line=dict(color='rgba(128,128,128,0.5)', width=1),
                fill='tonexty',
                fillcolor='rgba(128,128,128,0.1)',
            ),
            row=1, col=1
        )

    current_row = 2

    # 2. 거래량
    if show_volume and 'volume' in df.columns:
        colors = ['#26a69a' if c >= o else '#ef5350' for c, o in zip(df['close'], df['open'])]
        fig.add_trace(
            go.Bar(x=x_data, y=df['volume'], name='Volume', marker_color=colors),
            row=current_row, col=1
        )

        # 거래량 MA
        if 'volume_ma20' in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=x_data, y=df['volume_ma20'],
                    name='Vol MA20',
                    line=dict(color='orange', width=1),
                ),
                row=current_row, col=1
            )
        current_row += 1

    # 3. MACD
    if show_macd and 'macd' in df.columns:
        fig.add_trace(
            go.Scatter(x=x_data, y=df['macd'], name='MACD', line=dict(color='#2196f3', width=1.5)),
            row=current_row, col=1
        )
        fig.add_trace(
            go.Scatter(x=x_data, y=df['macd_signal'], name='Signal', line=dict(color='#ff9800', width=1.5)),
            row=current_row, col=1
        )

        # 히스토그램
        if 'macd_hist' in df.columns:
            colors_hist = ['#26a69a' if v >= 0 else '#ef5350' for v in df['macd_hist']]
            fig.add_trace(
                go.Bar(x=x_data, y=df['macd_hist'], name='Histogram', marker_color=colors_hist, opacity=0.5),
                row=current_row, col=1
            )
        current_row += 1

    # 4. RSI
    if show_rsi and 'rsi' in df.columns:
        fig.add_trace(
            go.Scatter(x=x_data, y=df['rsi'], name='RSI', line=dict(color='#9c27b0', width=1.5)),
            row=current_row, col=1
        )
        # 과매수/과매도 라인
        fig.add_hline(y=70, line_dash="dash", line_color="red", opacity=0.5, row=current_row, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", opacity=0.5, row=current_row, col=1)
        fig.add_hline(y=50, line_dash="dot", line_color="gray", opacity=0.3, row=current_row, col=1)

    # 레이아웃
    fig.update_layout(
        height=height,
        xaxis_rangeslider_visible=False,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=50, r=20, t=40, b=20),
        hovermode='x unified',
    )

    # Y축 설정
    fig.update_yaxes(title_text="Price", row=1, col=1)

    return fig


def create_mini_chart(
    df: pd.DataFrame,
    width: int = 200,
    height: int = 80,
) -> go.Figure:
    """미니 스파크라인 차트"""
    x_data = df['timestamp'] if 'timestamp' in df.columns else df.index

    # 색상 결정 (상승/하락)
    if len(df) > 1:
        change = df['close'].iloc[-1] - df['close'].iloc[0]
        color = '#26a69a' if change >= 0 else '#ef5350'
    else:
        color = '#6b7280'

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=x_data,
            y=df['close'],
            mode='lines',
            line=dict(color=color, width=1.5),
            fill='tozeroy',
            fillcolor=f'rgba{tuple(list(int(color.lstrip("#")[i:i+2], 16) for i in (0, 2, 4)) + [0.1])}',
        )
    )

    fig.update_layout(
        width=width,
        height=height,
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        showlegend=False,
        hovermode=False,
    )

    return fig


def create_technical_summary(df: pd.DataFrame) -> Dict[str, Any]:
    """기술적 분석 요약"""
    if df is None or df.empty:
        return {}

    latest = df.iloc[-1]

    summary = {
        "price": latest['close'],
        "change_1d": (latest['close'] / df.iloc[-2]['close'] - 1) * 100 if len(df) > 1 else 0,
    }

    # MA 상태
    ma_status = []
    for period in [20, 50, 200]:
        col = f'ma{period}'
        if col in df.columns and pd.notna(latest.get(col)):
            above = latest['close'] > latest[col]
            ma_status.append({
                "period": period,
                "value": latest[col],
                "above": above,
                "distance": (latest['close'] / latest[col] - 1) * 100,
            })
    summary["ma_status"] = ma_status

    # RSI
    if 'rsi' in df.columns and pd.notna(latest.get('rsi')):
        rsi = latest['rsi']
        if rsi >= 70:
            rsi_signal = "과매수"
        elif rsi <= 30:
            rsi_signal = "과매도"
        else:
            rsi_signal = "중립"
        summary["rsi"] = {"value": rsi, "signal": rsi_signal}

    # MACD
    if 'macd' in df.columns and 'macd_signal' in df.columns:
        macd = latest.get('macd', 0)
        signal = latest.get('macd_signal', 0)
        hist = latest.get('macd_hist', 0)

        if pd.notna(macd) and pd.notna(signal):
            if macd > signal:
                macd_signal = "상승"
            else:
                macd_signal = "하락"
            summary["macd"] = {"macd": macd, "signal": signal, "hist": hist, "trend": macd_signal}

    # 볼린저 밴드
    if 'bb_pct' in df.columns and pd.notna(latest.get('bb_pct')):
        bb_pct = latest['bb_pct']
        if bb_pct >= 1:
            bb_signal = "상단 돌파"
        elif bb_pct <= 0:
            bb_signal = "하단 이탈"
        elif bb_pct >= 0.8:
            bb_signal = "상단 근접"
        elif bb_pct <= 0.2:
            bb_signal = "하단 근접"
        else:
            bb_signal = "밴드 내"
        summary["bb"] = {"pct": bb_pct, "signal": bb_signal}

    # 거래량
    if 'volume_ratio' in df.columns and pd.notna(latest.get('volume_ratio')):
        vol_ratio = latest['volume_ratio']
        if vol_ratio >= 2.0:
            vol_signal = "급증"
        elif vol_ratio >= 1.5:
            vol_signal = "증가"
        elif vol_ratio <= 0.5:
            vol_signal = "급감"
        else:
            vol_signal = "보통"
        summary["volume"] = {"ratio": vol_ratio, "signal": vol_signal}

    return summary


def get_signal_color(signal: str) -> str:
    """시그널에 따른 색상 반환"""
    bullish = ["상승", "과매도", "하단 이탈", "하단 근접", "급증"]
    bearish = ["하락", "과매수", "상단 돌파", "상단 근접"]

    if signal in bullish:
        return "#26a69a"
    elif signal in bearish:
        return "#ef5350"
    return "#6b7280"


def add_signal_overlay(
    fig: go.Figure,
    df: pd.DataFrame,
    signal_data: Dict[str, Any],
    row: int = 1,
) -> go.Figure:
    """
    차트에 시그널 오버레이 추가

    Args:
        fig: plotly Figure
        df: OHLCV DataFrame
        signal_data: 시그널 정보 딕셔너리
            - direction: "bullish" or "bearish"
            - zone_high: 존 상단
            - zone_low: 존 하단
            - entry_price: 진입가
            - stop_loss: 손절가
            - take_profit_1: TP1
            - take_profit_2: TP2
            - trigger_idx: 트리거 캔들 인덱스 (optional)
        row: 차트 행 번호
    """
    x_data = df['timestamp'] if 'timestamp' in df.columns else df.index
    x_start = x_data.iloc[0]
    x_end = x_data.iloc[-1]

    is_bullish = signal_data.get('direction', 'bullish') == 'bullish'

    # 색상 설정
    zone_color = 'rgba(38, 166, 154, 0.2)' if is_bullish else 'rgba(239, 83, 80, 0.2)'  # 녹색/빨간색 반투명
    zone_border = '#26a69a' if is_bullish else '#ef5350'
    entry_color = '#2196f3'  # 파란색
    sl_color = '#ef5350'  # 빨간색
    tp_color = '#26a69a'  # 녹색

    # 1. POI 존 (Zone) - 반투명 박스
    zone_high = signal_data.get('zone_high')
    zone_low = signal_data.get('zone_low')

    if zone_high and zone_low:
        # 존 영역 (음영)
        fig.add_shape(
            type="rect",
            x0=x_start, x1=x_end,
            y0=zone_low, y1=zone_high,
            fillcolor=zone_color,
            line=dict(color=zone_border, width=1, dash="dot"),
            row=row, col=1,
            layer="below",
        )

        # 존 라벨
        zone_label = "📍 POI Zone" if is_bullish else "📍 POI Zone"
        fig.add_annotation(
            x=x_end, y=(zone_high + zone_low) / 2,
            text=f"존: {zone_low:,.0f} - {zone_high:,.0f}",
            showarrow=False,
            font=dict(size=10, color=zone_border),
            bgcolor="white",
            bordercolor=zone_border,
            borderwidth=1,
            xanchor="right",
            row=row, col=1,
        )

    # 2. 진입가 (Entry) - 파란색 점선
    entry_price = signal_data.get('entry_price')
    if entry_price:
        fig.add_hline(
            y=entry_price,
            line_dash="dash",
            line_color=entry_color,
            line_width=2,
            annotation_text=f"진입: {entry_price:,.0f}",
            annotation_position="right",
            annotation_font_size=10,
            annotation_font_color=entry_color,
            row=row, col=1,
        )

    # 3. 손절가 (Stop Loss) - 빨간색 점선
    stop_loss = signal_data.get('stop_loss')
    if stop_loss:
        fig.add_hline(
            y=stop_loss,
            line_dash="dot",
            line_color=sl_color,
            line_width=2,
            annotation_text=f"SL: {stop_loss:,.0f}",
            annotation_position="right",
            annotation_font_size=10,
            annotation_font_color=sl_color,
            row=row, col=1,
        )

    # 4. TP1, TP2 - 녹색 점선
    tp1 = signal_data.get('take_profit_1')
    tp2 = signal_data.get('take_profit_2')

    if tp1:
        fig.add_hline(
            y=tp1,
            line_dash="dashdot",
            line_color=tp_color,
            line_width=1.5,
            annotation_text=f"TP1: {tp1:,.0f}",
            annotation_position="right",
            annotation_font_size=10,
            annotation_font_color=tp_color,
            row=row, col=1,
        )

    if tp2:
        fig.add_hline(
            y=tp2,
            line_dash="dashdot",
            line_color=tp_color,
            line_width=1.5,
            annotation_text=f"TP2: {tp2:,.0f}",
            annotation_position="right",
            annotation_font_size=10,
            annotation_font_color=tp_color,
            row=row, col=1,
        )

    # 5. 트리거 캔들 하이라이트
    trigger_idx = signal_data.get('trigger_idx')
    if trigger_idx is not None and 0 <= trigger_idx < len(df):
        trigger_x = x_data.iloc[trigger_idx]
        trigger_low = df.iloc[trigger_idx]['low']
        trigger_high = df.iloc[trigger_idx]['high']

        # 트리거 캔들에 원형 마커
        fig.add_trace(
            go.Scatter(
                x=[trigger_x],
                y=[trigger_low * 0.995],  # 캔들 아래에 표시
                mode='markers+text',
                marker=dict(
                    symbol='triangle-up' if is_bullish else 'triangle-down',
                    size=15,
                    color=zone_border,
                ),
                text=['🎯'],
                textposition='bottom center',
                name='트리거',
                showlegend=False,
            ),
            row=row, col=1
        )

    return fig


def create_signal_chart(
    df: pd.DataFrame,
    signal_data: Dict[str, Any],
    symbol: str = "",
    show_ma: List[int] = [20, 50],
    show_bb: bool = True,
    show_volume: bool = True,
    height: int = 600,
) -> go.Figure:
    """
    시그널 정보가 포함된 차트 생성

    기본 캔들스틱 차트에 시그널 오버레이를 추가합니다.
    """
    # 기본 차트 생성
    fig = create_candlestick_chart(
        df=df,
        symbol=symbol,
        show_ma=show_ma,
        show_bb=show_bb,
        show_volume=show_volume,
        show_macd=False,
        show_rsi=False,
        height=height,
    )

    # 시그널 오버레이 추가
    if signal_data:
        fig = add_signal_overlay(fig, df, signal_data, row=1)

    # 레이아웃 업데이트 - 시그널 정보 표시
    direction_text = "🟢 롱" if signal_data.get('direction') == 'bullish' else "🔴 숏"
    pattern_type = signal_data.get('pattern_type', '')

    fig.update_layout(
        title=dict(
            text=f"{symbol} - {direction_text} {pattern_type}",
            font=dict(size=16),
        ),
    )

    return fig
