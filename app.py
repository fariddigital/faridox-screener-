import streamlit as st
import yfinance as yf
import pandas as pd
import concurrent.futures
from finvizfinance.screener.overview import Overview

# إعدادات الصفحة والتصميم الداكن
st.set_page_config(page_title="Faridox Auto-Filter", layout="wide", page_icon="🚀")

st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #FF4B4B; color: white; }
    </style>
""", unsafe_allow_html=True)

st.title("🚀 Faridox Filter Pro (Auto-Scanner)")
st.subheader("ماسح السوق الآلي - استراتيجية فريدوكس")

def analyze_ticker(ticker):
    """تحليل السهم بناءً على شروط فريدوكس السبعة"""
    try:
        stock = yf.Ticker(ticker)
        # جلب بيانات 3 أشهر للحسابات الفنية
        hist = stock.history(period="3mo")
        if len(hist) < 50: return None
            
        info = stock.info
        current_close = hist['Close'].iloc[-1]
        prev_close = hist['Close'].iloc[-2]
        current_vol = hist['Volume'].iloc[-1]
        
        # 1. السعر بين 1 و 20
        if not (1 <= current_close <= 20): return None
        
        # 2. القيمة السوقية > 450 مليون
        market_cap = info.get('marketCap', 0)
        if market_cap < 450_000_000: return None
        
        # 3. حجم التداول الحالي > 100 ألف
        if current_vol < 100_000: return None
        
        # 4. الحسابات الفنية: SMA 50 و Rel Vol
        sma_50 = hist['Close'].rolling(window=50).mean().iloc[-1]
        avg_vol_10 = hist['Volume'].shift(1).rolling(window=10).mean().iloc[-1]
        rel_vol = current_vol / avg_vol_10 if avg_vol_10 > 0 else 0
        change_pct = ((current_close - prev_close) / prev_close) * 100
        
        # 5. السعر فوق SMA 50
        if current_close < sma_50: return None
        
        # 6. الارتفاع اليومي > 10%
        if change_pct < 10: return None
        
        # 7. الحجم النسبي > 2
        if rel_vol < 2: return None
        
        # 8. الفلوت (Float) < 50 مليون
        float_shares = info.get('floatShares', 0)
        if float_shares > 50_000_000 or float_shares == 0: return None

        return {
            "الرمز": ticker,
            "السعر ($)": round(current_close, 2),
            "التغير (%)": f"+{round(change_pct, 2)}%",
            "Rel Vol": round(rel_vol, 2),
            "Float": f"{int(float_shares/1e6)}M",
            "Mkt Cap": f"${int(market_cap/1e6)}M",
            "SMA 50": round(sma_50, 2)
        }
    except:
        return None

# واجهة المستخدم
st.sidebar.info("الشروط المطبقة: السعر (1-20$)، ماركت كاب > 450M، فلوت < 50M، فوليوم > 100K، Rel Vol > 2، ارتفاع > 10%، فوق SMA50.")

if st.button("🔍 ابدأ الفحص الآلي للسوق الآن"):
    with st.spinner("جاري سحب قائمة الأسهم النشطة من Finviz وفلترتها..."):
        try:
            # الخطوة 1: جلب قائمة أولية من Finviz (أسهم صغيرة مرتفعة السعر)
            foverview = Overview()
            # فلاتر أولية لتقليل عدد الأسهم وتسريع العملية
            filters_dict = {
                'Market Cap.': 'Small ($300mln to $2bln)', 
                'Price': 'Under $20',
                'Change': 'Up'
            }
            foverview.set_filter(filters_dict=filters_dict)
            df_initial = foverview.screener_view()
            
            if df_initial.empty:
                st.warning("لم يتم العثور على أسهم نشطة في السوق حالياً.")
            else:
                tickers = df_initial['Ticker'].tolist()
                st.write(f"تم العثور على {len(tickers)} سهم مرشح. جاري الفحص العميق...")
                
                results = []
                progress_bar = st.progress(0)
                
                # تنفيذ الفحص بالتوازي لتسريع العملية (Multithreading)
                with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                    futures = {executor.submit(analyze_ticker, t): t for t in tickers}
                    for i, future in enumerate(concurrent.futures.as_completed(futures)):
                        res = future.result()
                        if res:
                            results.append(res)
                        progress_bar.progress((i + 1) / len(tickers))
                
                if results:
                    st.success(f"تم العثور على {len(results)} سهم تطابق استراتيجية فريدوكس تماماً!")
                    final_df = pd.DataFrame(results)
                    st.dataframe(final_df, use_container_width=True, hide_index=True)
                else:
                    st.warning("لا يوجد أسهم تطابق 'كل' شروط الاستراتيجية في هذه اللحظة.")
                    
        except Exception as e:
            st.error(f"حدث خطأ أثناء الاتصال بالسوق: {e}")

st.divider()
st.caption("ملاحظة: البيانات تظهر بحسب آخر إغلاق أو تحديث من Yahoo Finance.")
