import pandas as pd
import time
import logging
from typing import Optional
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, 
    NoSuchElementException, 
    WebDriverException
)
from webdriver_manager.chrome import ChromeDriverManager

# ロギングの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class StockScraper:
    """Seleniumを使用して株価データを取得するクラス"""
    
    def __init__(self, webdriver_path=None, headless=True):
        """WebDriverを初期化する
        
        Args:
            webdriver_path (str, optional): WebDriverのパス。Noneの場合は自動ダウンロード。
            headless (bool, optional): ヘッドレスモードで実行するかどうか。デフォルトはTrue。
        """
        try:
            # Chromeオプションの設定
            chrome_options = Options()
            if headless:
                chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            # Bot対策のためのUser-Agent設定
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36')
            
            # WebDriverの初期化
            if webdriver_path:
                service = Service(executable_path=webdriver_path)
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                # webdriver-managerを使用して自動ダウンロード
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # タイムアウト設定
            self.driver.implicitly_wait(10)  # 暗黙的な待機時間（秒）
            self.driver.set_page_load_timeout(30)  # ページロードタイムアウト（秒）
            
            logger.info("WebDriverが正常に初期化されました")
        except Exception as e:
            logger.error(f"WebDriverの初期化に失敗しました: {str(e)}")
            raise
    
    def get_stock_data(self, stock_code: str) -> Optional[pd.DataFrame]:
        """指定された銘柄コードの株価データを取得する
        
        Args:
            stock_code (str): 銘柄コード（例: "7203"）
            
        Returns:
            Optional[pd.DataFrame]: 株価データを含むDataFrame。失敗時はNone。
        """
        try:
            # 株探のURLを生成
            url = f"https://kabutan.jp/stock/kabuka?code={stock_code}"
            logger.info(f"URL: {url} にアクセスします")
            
            # ページにアクセス
            self.driver.get(url)
            
            # 株価テーブルが表示されるまで待機
            # 修正：正しいCSSセレクタを使用
            wait = WebDriverWait(self.driver, 10)
            stock_table_container = wait.until(EC.presence_of_element_located((By.ID, "stock_kabuka_table")))
            
            # 過去の株価データテーブルを取得
            stock_table = stock_table_container.find_element(By.CSS_SELECTOR, "table.stock_kabuka_dwm")
            
            # テーブルのHTML取得
            table_html = stock_table.get_attribute('outerHTML')
            
            # HTMLからテーブルを解析する前にログを出力
            logger.info(f"テーブルHTML（先頭200文字）: {table_html[:200]}...")
            
            # Pandasでテーブルを解析
            dfs = pd.read_html(table_html)
            
            # 通常、最初のテーブルが目的のデータを含む
            df = dfs[0]
            
            # 解析直後のデータフレーム構造を確認
            logger.info(f"解析後のデータフレーム構造: {df.head(1).to_dict()}")
            logger.info(f"カラム: {df.columns.tolist()}")
            
            # データの整形
            # カラム名を整理（サイトの構造に応じて調整が必要）
            if len(df.columns) >= 8:  # 必要なカラム数があるか確認
                df.columns = ['日付', '始値', '高値', '安値', '終値', '前日比', '前日比％', '売買高(株)']
                
                # 日付データの確認（処理前）
                logger.info(f"日付列の最初の値（処理前）: {df['日付'].iloc[0]}, 型: {type(df['日付'].iloc[0])}")
                
                # データクレンジング
                for col in ['始値', '高値', '安値', '終値', '前日比']:
                    df[col] = df[col].astype(str).str.replace(',', '').str.replace('---', 'NaN')
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                
                # 前日比％からパーセント記号を削除
                df['前日比％'] = df['前日比％'].astype(str).str.replace('%', '').str.replace('---', 'NaN')
                df['前日比％'] = pd.to_numeric(df['前日比％'], errors='coerce')
                
                # 売買高から単位と区切り文字を削除
                df['売買高(株)'] = df['売買高(株)'].astype(str).str.replace(',', '').str.replace('株', '').str.replace('---', 'NaN')
                df['売買高(株)'] = pd.to_numeric(df['売買高(株)'], errors='coerce')
                
                # 日付をdatetime型に変換（YY/MM/DD形式に対応）
                # 元の文字列を保持
                df['元の日付'] = df['日付'].copy()
                
                # 日付が既に文字列ではなくdatetime型である場合、文字列に変換する
                if pd.api.types.is_datetime64_any_dtype(df['日付']):
                    df['日付'] = df['日付'].dt.strftime('%y/%m/%d')
                
                # YY/MM/DD形式に対応
                try:
                    df['日付'] = pd.to_datetime(df['日付'], format='%y/%m/%d', errors='coerce')
                    logger.info(f"YY/MM/DD形式で変換を試行。最初の日付: {df['日付'].iloc[0]}")
                except Exception as e:
                    logger.error(f"日付変換エラー1: {str(e)}")
                    # 変換失敗した場合は別の形式を試す
                    try:
                        # YYYY/MM/DD形式も試す
                        df['日付'] = pd.to_datetime(df['元の日付'], format='%Y/%m/%d', errors='coerce')
                        logger.info(f"YYYY/MM/DD形式で変換を試行。最初の日付: {df['日付'].iloc[0]}")
                    except Exception as e2:
                        logger.error(f"日付変換エラー2: {str(e2)}")
                
                # 元の日付列を削除
                df = df.drop('元の日付', axis=1, errors='ignore')
                
                # 日付データの確認（処理後）
                logger.info(f"日付列の最初の値（処理後）: {df['日付'].iloc[0]}, 型: {type(df['日付'].iloc[0])}")
                
                # 日付でソート（降順）
                df = df.sort_values('日付', ascending=False).reset_index(drop=True)
                
                logger.info(f"銘柄コード {stock_code} のデータ取得に成功しました。行数: {len(df)}")
                return df
            else:
                logger.error(f"テーブルのカラム数が不足しています: {len(df.columns)}")
                return None
                
        except TimeoutException:
            logger.error("ページの読み込みがタイムアウトしました")
            return None
        except NoSuchElementException:
            logger.error("株価テーブルが見つかりませんでした。サイトの構造が変更された可能性があります。")
            return None
        except WebDriverException as e:
            logger.error(f"WebDriverエラー: {str(e)}")
            return None
        except ValueError as e:
            logger.error(f"データ変換エラー: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"予期しないエラー: {str(e)}")
            return None
    
    def close_driver(self):
        """WebDriverを終了する"""
        if hasattr(self, 'driver'):
            try:
                self.driver.quit()
                logger.info("WebDriverが正常に終了しました")
            except Exception as e:
                logger.error(f"WebDriverの終了に失敗しました: {str(e)}") 