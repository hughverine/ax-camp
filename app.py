import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import logging
import atexit
from data_loader import StockScraper

# ロギングの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# タイトルと説明
st.title('日経平均株価データ表示システム')
st.write('日経平均株価の日足データを表示します。')

# セッション状態の初期化
if 'scraper' not in st.session_state:
    st.session_state.scraper = None
if 'data' not in st.session_state:
    st.session_state.data = None

# WebDriverのクリーンアップ関数
def cleanup():
    if 'scraper' in st.session_state and st.session_state.scraper is not None:
        try:
            st.session_state.scraper.close_driver()
            st.session_state.scraper = None
            logger.info("WebDriverをクリーンアップしました")
        except Exception as e:
            logger.error(f"WebDriverのクリーンアップに失敗しました: {str(e)}")

# プログラム終了時にクリーンアップを実行するよう登録
atexit.register(cleanup)

# データ取得ボタン
if st.button('データ取得'):
    # WebDriverの初期化（まだ初期化されていない場合）
    if st.session_state.scraper is None:
        try:
            with st.spinner('WebDriverを初期化中...'):
                st.session_state.scraper = StockScraper(headless=True)
        except Exception as e:
            st.error(f"WebDriverの初期化に失敗しました: {str(e)}")
            st.stop()
    
    # 日経平均株価（コード0000）のデータ取得
    try:
        with st.spinner('日経平均株価のデータを取得中...'):
            stock_code = "0000"  # 日経平均株価の銘柄コード
            df = st.session_state.scraper.get_stock_data(stock_code)
            if df is not None and not df.empty:
                st.session_state.data = df  # セッションにデータを保存
            else:
                st.error("データの取得に失敗しました。Webサイトの構造が変更された可能性があります。")
                st.stop()
        
        if df is not None and not df.empty:
            # データテーブルの表示
            st.subheader('日経平均株価の日足データ')
            st.dataframe(df)
            
            # ローソク足チャート
            st.subheader('ローソク足チャート')
            # データを日付昇順に並べ替え（グラフ表示用）
            chart_df = df.sort_values('日付')
            candlestick = go.Figure(data=[go.Candlestick(
                x=chart_df['日付'],
                open=chart_df['始値'], 
                high=chart_df['高値'],
                low=chart_df['安値'], 
                close=chart_df['終値'],
                increasing_line_color='red',  # 上昇時の色
                decreasing_line_color='blue',  # 下降時の色
                name='ローソク足'
            )])
            candlestick.update_layout(
                xaxis_title='日付',
                yaxis_title='価格（円）',
                hovermode='x unified'
            )
            st.plotly_chart(candlestick, use_container_width=True)
        else:
            st.error("日経平均株価のデータ取得に失敗しました。")
    except Exception as e:
        st.error(f"エラーが発生しました: {str(e)}")
        import traceback
        st.error(traceback.format_exc())  # 詳細なエラー情報を表示
else:
    # 既に取得したデータがある場合は表示
    if st.session_state.data is not None:
        # データテーブルの表示
        st.subheader('日経平均株価の日足データ')
        st.dataframe(st.session_state.data)
        
        # ローソク足チャート
        st.subheader('ローソク足チャート')
        # データを日付昇順に並べ替え（グラフ表示用）
        chart_df = st.session_state.data.sort_values('日付')
        candlestick = go.Figure(data=[go.Candlestick(
            x=chart_df['日付'],
            open=chart_df['始値'], 
            high=chart_df['高値'],
            low=chart_df['安値'], 
            close=chart_df['終値'],
            increasing_line_color='red',  # 上昇時の色
            decreasing_line_color='blue',  # 下降時の色
            name='ローソク足'
        )])
        candlestick.update_layout(
            xaxis_title='日付',
            yaxis_title='価格（円）',
            hovermode='x unified'
        )
        st.plotly_chart(candlestick, use_container_width=True)

# フッター
st.write("---")
st.write("注意: このアプリはデモ用であり、表示されるデータの正確性は保証されません。投資判断には利用しないでください。") 