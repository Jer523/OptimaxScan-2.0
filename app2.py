import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageOps
import img2pdf
import io
import os
from pdf2image import convert_from_bytes

# =====================================================================
# 📍 1. 网页设置 | Page Setup
# =====================================================================
st.set_page_config(
    page_title="OPTIMAX SCAN",
    page_icon="OptimaxScan Icon.png",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# =====================================================================
# 📍 2. 图片处理引擎 | Image Processing Engine
# =====================================================================
def get_base64(path):
    """👉 转换图片为代码 | Convert image to code"""
    import base64
    try:
        with open(path,"rb") as f:
            return base64.b64encode(f.read()).decode()
    except: return ""

def get_image_status(pil_img, f_size_kb):
    """👉 判断文档类型 | Identify document type"""
    try:
        small_img = pil_img.convert('L').resize((400, 518))
        img_array = np.array(small_img)
        bg_only = cv2.medianBlur(img_array, 21)
        mean_val = np.mean(bg_only)
        std_val = np.std(bg_only)
        if (mean_val > 238 and std_val < 15) or (mean_val > 245 and std_val < 25):
            return "KEEP_FILE"
        return "SCAN_PROCESS"
    except:
        return "SCAN_PROCESS"

def process_and_compress_to_letter(pil_img):
    """👉 调整尺寸并压缩（保持原样不旋转）| Resize and compress (No rotation)"""
    pil_img = ImageOps.exif_transpose(pil_img) 
    
    canvas_w, canvas_h = 2550, 3300 
    margin = 0.02 
    canvas = Image.new('RGB', (canvas_w, canvas_h), (255, 255, 255))
    
    img_w, img_h = pil_img.size
    scale = min((canvas_w * (1 - margin * 2)) / img_w, (canvas_h * (1 - margin * 2)) / img_h)
    new_w, new_h = int(img_w * scale), int(img_h * scale)
    resized_img = pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    offset = ((canvas_w - new_w) // 2, (canvas_h - new_h) // 2)
    canvas.paste(resized_img, offset)
    
    q = 90
    output = io.BytesIO()
    canvas.save(output, format="JPEG", quality=q, optimize=True)
    while output.tell() / 1024 > 450 and q > 20:
        q -= 5
        output = io.BytesIO()
        canvas.save(output, format="JPEG", quality=q, optimize=True)
    return output.getvalue()

def process_scan_layered_from_mem(pil_img, is_small):
    """👉 清晰化文字（保持原样不旋转）| Enhance text (No rotation)"""
    pil_img = ImageOps.exif_transpose(pil_img) 
    img_cv = cv2.cvtColor(np.array(pil_img.convert('RGB')), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    
    if is_small:
        smooth = cv2.GaussianBlur(gray, (3, 3), 0)
        bg = cv2.medianBlur(smooth, 31)
        final = cv2.divide(smooth, bg, scale=245)
        clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(12, 12))
        final = clahe.apply(final)
        final = cv2.addWeighted(final, 1.22, cv2.GaussianBlur(final, (0, 0), 1.5), -0.22, 0)
    else:
        bg = cv2.medianBlur(gray, 51)
        final = cv2.divide(gray, bg, scale=255)
        final = cv2.fastNlMeansDenoising(final, None, h=12, templateWindowSize=7, searchWindowSize=21)
        final = cv2.addWeighted(final, 1.6, cv2.GaussianBlur(final, (0, 0), 4), -0.6, 0)
    
    return Image.fromarray(cv2.cvtColor(final, cv2.COLOR_GRAY2RGB))

# =====================================================================
# 📍 3. 图标素材 | Icon Assets
# =====================================================================
folder = get_base64("Folder.png")
star = get_base64("Star.png")
check_mark = get_base64("Check Mark.png")
download = get_base64("download.png")

# =====================================================================
# 📍 4. 网页外观 | App Design (CSS)
# =====================================================================
st.markdown("""
<style>

/* 基础排版 */
html,body,.stApp { height:100%; background:#F0F4F8; display:flex; flex-direction:column; }
.main .block-container { padding-top:10vh; max-width:750px; padding-bottom:120px; }

/* 标题卡片 */
.title-card{
    width:100%;
    background:#F0F4F8;
    border-radius:30px;
    box-shadow:15px 15px 35px #d1d9e6,-15px -15px 35px #ffffff;
    padding:45px 20px;
    text-align:center;
    margin-bottom:32px;
}

.main-title{
    font-weight:800;
    font-size:52px;
    background:linear-gradient(135deg,#64B8FF,#42F2BF);
    -webkit-background-clip:text;
    -webkit-text-fill-color:transparent;
}

.sub-title{
    color:#A0AEC0;
    font-size:16px;
    margin-top:10px;
}

/* =========================================================
   Sidebar 拟态阴影恢复
========================================================= */

[data-testid="stSidebar"]{
    background:#F0F4F8 !important;
    box-shadow: inset -10px 0 20px #d1d9e6 !important;
    border:none !important;
}

/* =========================================================
   Button
========================================================= */

div.stButton>button{
    background:#F0F4F8 !important;
    color:#64B8FF !important;
    border-radius:20px !important;
    border:none !important;
    box-shadow:10px 10px 20px #d1d9e6,-10px -10px 20px #ffffff !important;
    font-weight:bold !important;
    height:85px !important;
    width:100% !important;
}

div.stDownloadButton>button{
    background:#F0F4F8 !important;
    color:#64B8FF !important;
    border-radius:20px !important;
    border:none !important;
    box-shadow:10px 10px 20px #d1d9e6,-10px -10px 20px #ffffff !important;
    font-weight:bold !important;
    height:65px !important;
    width:100% !important;
}

/* =========================================================
   Upload Box
========================================================= */

.stFileUploader,[data-testid="stFileUploader"]{
    background:#F0F4F8 !important;
    border-radius:20px !important;
    box-shadow: inset 8px 8px 16px #d1d9e6,
                inset -8px -8px 16px #ffffff !important;
    padding:20px !important;
}

/* =========================================================
   手机端 uploader 布局恢复
========================================================= */

@media (max-width:768px){

[data-testid="stFileUploader"] section{
display:flex !important;
flex-direction:column !important;
align-items:center !important;
justify-content:center !important;
padding:20px 10px !important;
}

[data-testid="stFileUploader"] section button{
display:inline-flex !important;
margin:10px auto !important;
position:static !important;
float:none !important;
}

[data-testid="stFileUploaderDropzone"]{
display:flex !important;
justify-content:center !important;
align-items:center !important;
width:100% !important;
min-height:150px !important;
}

[data-testid="stFileUploaderDropzone"]>div{
display:flex !important;
flex-direction:column !important;
align-items:center !important;
justify-content:center !important;
width:100% !important;
text-align:center !important;
}

}

/* =========================================================
   Progress Bar 流光恢复
========================================================= */

div[data-testid="stProgressBar"]{
margin-left:0.25em;
position:relative;
overflow:hidden;
}

.stProgress>div>div{
background-color:transparent !important;
border-radius:10px !important;
height:8px !important;
box-shadow:none !important;
}

.stProgress>div>div>div>div{
background:linear-gradient(to right,#64B8FF,#42F2BF) !important;
border-radius:10px !important;
position:relative;
overflow:hidden;
}

.stProgress>div>div>div>div::after{
content:"";
position:absolute;
top:0;
left:-40%;
width:40%;
height:100%;
background:linear-gradient(
90deg,
transparent,
rgba(255,255,255,0.35),
transparent
);
animation:optimaxShine 2s linear infinite;
}

@keyframes optimaxShine{
0%{left:-40%;}
100%{left:120%;}
}



</style>
""", unsafe_allow_html=True)

# =====================================================================
# 📍 5. 静态界面 | Static UI
# =====================================================================

with st.sidebar:
    st.markdown('<div class="sidebar-card">设置 | SETTINGS</div>', unsafe_allow_html=True)
    st.info("💡 提示：支持 PDF, PNG, JPG 及 HEIC 格式。")

st.markdown("""
<div class="title-card">
<div class="main-title">OPTIMAX SCAN</div>
<div class="sub-title">Refining your vision, one pixel at a time.</div>
</div>
""", unsafe_allow_html=True)

uploaded_files = st.file_uploader("", accept_multiple_files=True, label_visibility="collapsed")

# =====================================================================
# 📍 6. 交互逻辑 | Interaction Logic
# =====================================================================

if uploaded_files:

    st.markdown(f'<div class="queued-title" style="visibility:hidden;height:0;"><img src="data:image/png;base64,{folder}"></div>', unsafe_allow_html=True)

    st.markdown(f'''
    <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:120px;pointer-events:none;position:relative;z-index:10;">
      <div style="display:flex;align-items:center;justify-content:center;">
        <img src="data:image/png;base64,{star}" style="width:25px;margin-right:10px;">
        <span style="color:#64B8FF;font-weight:600;">开始优化 | START REFINING</span>
      </div>
      <div id="progress-slot" style="width:85%;height:8px;border-radius:10px;box-shadow: inset 4px 4px 8px #d1d9e6, inset -4px -4px 8px #ffffff;background:#F0F4F8;margin-top:8px;"></div>
    </div>
    ''', unsafe_allow_html=True)

    st.markdown('<style>div[data-testid="stProgress"]{ width:85%; margin:auto; margin-top:-75px; position:relative; z-index:50; } div[data-testid="stVerticalBlock"] > div:has(div.stButton) { margin-top:-128px !important; }</style>', unsafe_allow_html=True)

    if st.button(" ", use_container_width=True, key="refine_btn"):

        all_processed_bytes=[]
        progress_bar=st.progress(0)

        for idx,file in enumerate(uploaded_files):

            file_bytes=file.read()

            temp_images=[]

            if file.name.lower().endswith('.pdf'):

                pages=convert_from_bytes(file_bytes)
                temp_images.extend(pages)

            else:

                img=Image.open(io.BytesIO(file_bytes))
                temp_images.append(img)

            for pil_img in temp_images:

                status=get_image_status(pil_img,len(file_bytes)/1024)

                if status=="KEEP_FILE":
                    page_bytes=process_and_compress_to_letter(pil_img)

                else:
                    processed_img=process_scan_layered_from_mem(pil_img,(len(file_bytes)/1024)<200)
                    page_bytes=process_and_compress_to_letter(processed_img)

                all_processed_bytes.append(page_bytes)

            progress_bar.progress((idx+1)/len(uploaded_files))

        st.markdown(f'''<div class="status-text" style="display:flex;align-items:center;justify-content:center;"><img src="data:image/png;base64,{check_mark}" style="width:22px;margin-right:8px;"> 处理完成 | TASKS COMPLETE</div>''',unsafe_allow_html=True)

        st.markdown(f'''<div style="display:flex;align-items:center;justify-content:center;height:65px;pointer-events:none;position:relative;z-index:10;"><img src="data:image/png;base64,{download}" style="width:25px;margin-right:10px;"><span style="color:#64B8FF;font-weight:600;">保存文件 | DOWNLOAD PDF</span></div>''',unsafe_allow_html=True)

        st.markdown('<style>div.stDownloadButton { margin-top:-92px !important; }</style>',unsafe_allow_html=True)

        final_pdf=img2pdf.convert(all_processed_bytes)

        st.download_button(
            label=" ",
            data=final_pdf,
            file_name="Optimax_Refined.pdf",
            mime="application/pdf",
            use_container_width=True
        )

# =====================================================================
# 📍 7. 页面底部 | Footer
# =====================================================================

/* Footer */

.footer{
position:fixed;
bottom:0;
left:0;
width:100%;
background:#F0F4F8;
text-align:center;
color:#BDC3C7;
font-size:13px;
padding-bottom:20px;
z-index:999;
}

st.markdown('<div class="footer">Optimax Scan Engine v2.0 | © 2026 Jerry Yin</div>',unsafe_allow_html=True)
