import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageOps
import img2pdf
import io
import base64
from pdf2image import convert_from_bytes

# --- 1. 深度拟态 UI 配置 ---
st.set_page_config(
    page_title="OPTIMAX SCAN",
    page_icon="OptimaxScan Icon.png",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- 2. 注入 CSS ---
st.markdown("""
<style>
/* 全局基础 */
html,body,.stApp { height:100%; background:#F0F4F8; display:flex; flex-direction:column; }
.main .block-container { padding-top:10vh; max-width:750px; padding-bottom: 120px; }

/* 标题卡片 */
.title-card { 
    width: 100%; background:#F0F4F8; border-radius:30px; 
    box-shadow:15px 15px 35px #d1d9e6, -15px -15px 35px #ffffff; 
    padding:45px 20px; text-align:center; margin-bottom:32px; 
}
.main-title { 
    font-weight:800; font-size:52px; 
    background:linear-gradient(135deg,#64B8FF,#42F2BF); 
    -webkit-background-clip:text; -webkit-text-fill-color:transparent; margin:0; 
}
.sub-title { color:#A0AEC0; font-size:16px; margin-top:10px; }

/* 状态文字居中 */
.status-text { 
    color:#64B8FF !important; font-weight:600; 
    display: flex !important; justify-content: center !important; 
    align-items: center !important; width: 100% !important;
    margin: 20px 0 28px 0 !important; 
}

/* 拟态按钮通用样式 */
div.stButton>button, div.stDownloadButton>button { 
    background:#F0F4F8 !important; color:#64B8FF !important; border-radius:20px !important; border:none !important; 
    box-shadow:10px 10px 20px #d1d9e6, -10px -10px 20px #ffffff !important; font-weight:bold !important; height:65px !important; width:100% !important; 
}
button:active,
div.stButton>button:active,
div.stDownloadButton>button:active,
[data-testid="stFileUploader"] button:active { 
    box-shadow: inset 6px 6px 12px #d1d9e6, inset -6px -6px 12px #ffffff !important;
    transform: translateY(2px) !important; 
}

[data-testid="stFileUploaderDropzone"] {
    background-color: transparent !important;
    border: none !important;
    display: flex !important;
}

/* 手机端精准适配 */
@media (max-width: 768px) {
    /* 标题微调 */
    .main-title { font-size: 9vw !important; white-space: nowrap !important; }
    
    /* 上传组件的父容器 Flex 居中 */
    [data-testid="stFileUploader"] section {
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
        padding: 20px 10px !important;
    }

    /* Browse files 按钮居中并重置定位 */
    [data-testid="stFileUploader"] section button {
        display: inline-flex !important;
        margin: 10px auto !important;
        position: static !important;
        float: none !important;
    }
    
    /* 核心 3：上传文字居中 */
   [data-testid="stFileUploaderDropzone"] {
    background-color: transparent !important;
    border: none !important;
    display: flex !important;
    justify-content: center !important;
    align-items: center !important;
    width: 100% !important;
    min-height: 150px !important; /* 保证凹陷区有足够高度 */
}

/* 穿透到内部文字容器，强制其内容水平居中 */
[data-testid="stFileUploaderDropzone"] > div {
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    justify-content: center !important;
    width: 100% !important;
    text-align: center !important;
}

</style>
""", unsafe_allow_html=True)

def get_base64(path):
    try:
        with open(path,"rb") as f:
            return base64.b64encode(f.read()).decode()
    except: return ""

folder=get_base64("Folder.png")
star=get_base64("Star.png")
check_mark=get_base64("Check Mark.png")
download=get_base64("download.png")

# --- 2. 注入原始脚本的核心功能内核 ---

def get_image_status(pil_img, f_size_kb):
    """智能检测：判断是扫描件还是原生数字文件"""
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
    """核心功能：Letter Size 布局 + 450KB 体积压缩逻辑"""
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
    """原始内核：分层图像处理算法"""
    img_cv = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
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

# --- 3. 进度条动画 ---
st.markdown("""
<style>
.stFileUploader{ background: #F0F4F8 !important;
    border-radius: 20px !important;
    box-shadow: inset 8px 8px 16px #d1d9e6, inset -8px -8px 16px #ffffff !important;
    padding: 20px !important;
    border: 1px solid rgba(255,255,255,0.5) !important; }

/* 按钮动画 */
button[kind="secondary"], div.stButton>button, div.stDownloadButton>button { transition: all .1s ease-in-out !important; }
button[kind="secondary"]{ background:#F0F4F8 !important; color:#64B8FF !important; border-radius:12px !important; box-shadow:4px 4px 8px #d1d9e6,-4px -4px 8px #ffffff !important; padding:0px 25px !important; height:38px !important; margin:10px 0 !important; border:none !important; }

/* --- 进度条流动与流光核 --- */
div[data-testid="stProgressBar"]{
    margin-left:0.25em;
    position:relative;
    overflow:hidden;
}

.stProgress > div > div { 
    background-color: transparent !important; 
    border-radius: 10px !important; 
    height: 8px !important; 
    box-shadow: none !important; 
}

/* 进度条主体与平滑过渡 */
.stProgress > div > div > div > div { 
    background: linear-gradient(to right, #64B8FF, #42F2BF) !important; 
    border-radius: 10px !important; 
    position: relative;
    overflow: hidden;
}

/* 进度条流光动画 (来自 14 copy.py) */
.stProgress > div > div > div > div::after {
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
    animation:optimaxShine 2s linear infinite; /* 核心：恢复流光动画 */
}

@keyframes optimaxShine{
    0%{ left:-40%; }
    100%{ left:120%; }
}

.footer{ position: fixed; bottom: 0; left: 0; width: 100%; background: #F0F4F8; text-align:center; color:#BDC3C7; font-size:13px; padding-bottom:20px; padding-top:10px; z-index: 999; }
</style>
""",unsafe_allow_html=True)

# --- 4. 侧边栏 ---
st.markdown("""
<style>
/* 侧边栏基础拟态 */
[data-testid="stSidebar"] {
    background-color: #F0F4F8 !important;
    box-shadow: inset -10px 0 20px #d1d9e6 !important;
    border: none !important;
}

/* 侧边栏卡片：保持和主界面一致的凸起感 */
.sidebar-card {
    background: #F0F4F8;
    border-radius: 20px;
    padding: 20px;
    margin: 15px;
    box-shadow: 6px 6px 12px #d1d9e6, -6px -6px 12px #ffffff;
    color: #64B8FF;
    font-weight: 600;
    text-align: center;
    margin-bottom: 30px;
}
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown('''
    <div class="sidebar-card">
        <div style="text-align: center; font-size: 1.1em; font-weight: 600; margin-bottom: 1px;">
            支持格式 | FORMATS
        </div>
        <div style="text-align: center; font-size: 0.95em; color: #A0AEC0; font-weight: 400; line-height: 1.6; letter-spacing: 1.2px; margin-bottom: 10px;">
            PDF, JPG, PNG, HEIC
        </div>
        <div style="text-align: center; font-size: 0.95em; color: #A0AEC0; font-weight: 400; line-height: 1.4; margin-bottom: 1px;">
            支持多种格式批量上传
        </div>
        <div style="text-align: center; font-size: 0.94em; color: #A0AEC0; font-weight: 400; line-height: 1.6; letter-spacing: 0.7px">
            Mixed-format uploads
        </div>
    </div>
        
    <div class="sidebar-card">
        <div style="text-align: center; font-size: 1.1em; color: #64B8FF; font-weight: 600; margin-bottom: 10px">
            上传提示 | TUTORIAL
        </div>
        <div style="text-align: left; font-size: 0.9em; color: #A0AEC0; font-weight: 400; line-height: 1.6; margin-left: 14px">
            1. 上传素材 | Upload Files<br>
        </div>
        <div style="text-align: left; font-size: 0.9em; color: #A0AEC0; font-weight: 400; line-height: 1.6; margin-left: 14px">
            2. 智能优化 | Start Refining
        </div>
            <div style="text-align: left; font-size: 0.7em; color: #A0AEC0; font-weight: 400; line-height: 1.6; letter-spacing: 0.7px; margin-left: 14px">
            分析: 光线/清晰度自适应修复<br>
            Auto-fix light and clarity<br>
            压缩: 体积优化，画质无损<br>
            CLossless Size Optimization<br>
            排版: 统一 Letter Size 布局<br>
            Standard 8.5×11 Layout
        </div>
        <div style="text-align: left; font-size: 0.9em; color: #A0AEC0; font-weight: 400; line-height: 1.6; margin-left: 14px">  
            3. 获取黑白件 | Export B&W
        </div>
    </div>
    ''', unsafe_allow_html=True)

# --- 5. 业务逻辑 ---

st.markdown("""
<div class="title-card">
<div class="main-title">OPTIMAX SCAN</div>
<div class="sub-title">Refining your vision, one pixel at a time.</div>
</div>
""",unsafe_allow_html=True)

uploaded_files=st.file_uploader("",accept_multiple_files=True,label_visibility="collapsed")

if uploaded_files:
    st.markdown(
f'<div class="queued-title" style="visibility:hidden;height:0;margin:0;padding:0;"><img src="data:image/png;base64,{folder}" style="height:0;"> 待优化素材 | QUEUED</div>',
unsafe_allow_html=True
)
    st.markdown(f'''<div style="display:flex;align-items:center;justify-content:center;height:65px;pointer-events:none;position:relative;z-index:10;"><img src="data:image/png;base64,{star}" style="width:25px;margin-right:10px;"><span style="color:#64B8FF;font-weight:600;">开始优化 | START REFINING</span></div>''',unsafe_allow_html=True)
    st.markdown('<style>div[data-testid="stVerticalBlock"] > div:has(div.stButton) { margin-top:-92px !important; }</style>',unsafe_allow_html=True)

    if st.button(" ",use_container_width=True, key="refine_btn"):
        all_processed_bytes = []
        progress_bar=st.progress(0)
        
        for idx, file in enumerate(uploaded_files):
            file_bytes = file.read()
            file_size_kb = len(file_bytes) / 1024
            
            temp_images = []
            if file.name.lower().endswith('.pdf'):
                try:
                    pages = convert_from_bytes(file_bytes)
                    temp_images.extend(pages)
                except: continue
            else:
                pil_img = ImageOps.exif_transpose(Image.open(io.BytesIO(file_bytes))).convert("RGB")
                temp_images.append(pil_img)
            
            for pil_img in temp_images:
                status = get_image_status(pil_img, file_size_kb)
                if status == "KEEP_FILE":
                    page_bytes = process_and_compress_to_letter(pil_img)
                else:
                    processed_img = process_scan_layered_from_mem(pil_img, file_size_kb < 200)
                    page_bytes = process_and_compress_to_letter(processed_img)
                all_processed_bytes.append(page_bytes)
            
            progress_bar.progress((idx+1)/len(uploaded_files))

        st.markdown(f'''<div class="status-text" style="display:flex;align-items:center;letter-spacing:-0.35px;"><img src="data:image/png;base64,{check_mark}" style="width:22px;margin-right:8px;"> 处理完成 | TASKS COMPLETE</div>''',unsafe_allow_html=True)
        st.markdown(f'''<div style="display:flex;align-items:center;justify-content:center;height:65px;pointer-events:none;position:relative;z-index:10;"><img src="data:image/png;base64,{download}" style="width:25px;margin-right:10px;"><span style="color:#64B8FF;font-weight:600;">保存文件 | DOWNLOAD PDF</span></div>''',unsafe_allow_html=True)
        st.markdown('<style>div.stDownloadButton { margin-top:-92px !important; }</style>',unsafe_allow_html=True)

        final_pdf = img2pdf.convert(all_processed_bytes)
        st.download_button(label=" ", data=final_pdf, file_name="Optimax_Refined.pdf", mime="application/pdf", use_container_width=True)

# --- 6. Footnotes ---

st.markdown('<div class="footer">Optimax Scan Engine v2.0 | © 2026 Jerry Yin</div>',unsafe_allow_html=True)
