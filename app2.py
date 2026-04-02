import streamlit as st
import streamlit.components.v1 as components
import cv2
cv2.setNumThreads(4)
import numpy as np
from PIL import Image, ImageOps
import img2pdf
import io
import base64
import time  # 精密阻尼器
from pdf2image import convert_from_bytes
from pillow_heif import register_heif_opener
register_heif_opener()

# --- 📍 1. 深度拟态 UI 配置 ---
st.set_page_config(
    page_title="OPTIMAX SCAN",
    page_icon="OptimaxScan Icon.png",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- 📍 2. 注入 CSS ---
st.markdown("""
<style>
/* 全局基础 */
html,body,.stApp { height:100%; background:#F0F4F8; display:flex; flex-direction:column; }
.main .block-container { padding-top:10vh; max-width:750px; padding-bottom: 120px; }

/* 标题卡片 */
.title-card { 
    width: 100%; background:#F0F4F8; border-radius:30px; 
    box-shadow:15px 15px 35px #d1d9e6, -15px -15px 35px #ffffff; 
    padding:45px 20px; text-align:center; margin-bottom:39px; 
}
.main-title {
    font-weight: 800;
    font-size: 52px;
    margin: 0;

    /* 第一层：极其克制的高光 (0.35) | 第二层：固定的蓝绿底色 */
    background-image: 
        linear-gradient(110deg, transparent 45%, rgba(255,255,255,0.35) 50%, transparent 55%),
        linear-gradient(135deg, #64B8FF, #42F2BF);

    /* 高光层拉伸到 300% 保证有足够的“助跑”距离，底色 100% 保持不动 */
    background-size: 500% 100%, 100% 100%;
    
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;

    /* 6.5s linear 确保匀速 */
    animation: pureShine 6.5s linear infinite;
}

@keyframes pureShine {
    /* 修正百分比：从 100% 到 0% 是最稳的循环方式 */
    0% {
        background-position: 100% 0, 0 0;
    }
    100% {
        background-position: 0% 0, 0 0;
    }
}
.sub-title { color:#A0AEC0; font-size:16px; margin-top:10px; }
@keyframes titleShimmer {
    0% { background-position: 200% center; }
    100% { background-position: -200% center; }
}
.sub-title { color:#A0AEC0; font-size:16px; margin-top:10px; }

/* 全站通用淡入动画引擎 */
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}
.fade-in-up { animation: fadeInUp 0.6s ease-out forwards; }

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
    box-shadow:10px 10px 20px #d1d9e6, -10px -10px 20px #ffffff !important; font-weight:bold !important; height:100px !important; width:100% !important; 
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
    overflow: visible !important;
}

[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] {
    display: flex !important;
    visibility: visible !important;
    height: auto !important;
    max-height: none !important;
    opacity: 1 !important;
}

[data-testid="stFileUploader"] section > div:first-child {
    display: flex !important;
    flex-direction: row !important;
    align-items: center !important;
    justify-content: space-between !important;
    width: 100% !important;
    flex-wrap: wrap !important;
}

/* 上传文件 */
.stFileUploader{ background: #F0F4F8 !important;
    border-radius: 20px !important;
    box-shadow: inset 8px 8px 16px #d1d9e6, inset -8px -8px 16px #ffffff !important;
    padding: 20px !important;
    margin-bottom:0px;
    border: 1px solid rgba(255,255,255,0.5) !important;
    
/* --- 新增：平滑平展动画 --- */
transition: max-height 0.6s cubic-bezier(0.4, 0, 0.2, 1), padding 0.6s ease !important;
    max-height: 2000px !important; 
    overflow: hidden !important;
}

/* 针对内部列表的平滑处理 */
[data-testid="stFileUploader"] ul {
    animation: fadeIn 0.5s ease-out forwards;
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(-5px); }
    to { opacity: 1; transform: translateY(0); }
}

/* 按钮动画 */
button[kind="secondary"], div.stButton>button, div.stDownloadButton>button { transition: all .1s ease-in-out !important; }
button[kind="secondary"]{ background:#F0F4F8 !important; color:#64B8FF !important; border-radius:12px !important; box-shadow:4px 4px 8px #d1d9e6,-4px -4px 8px #ffffff !important; padding:0px 25px !important; height:38px !important; margin:10px 0 !important; border:none !important; }

/* 为所有 PNG 图标添加高级感蓝色阴影 */
.element-container, .stMarkdown, div[data-testid="stVerticalBlock"] > div {
    overflow: visible !important;
}

/* 统一强效自然蓝阴影 */
img {
    /* 0.35 是透明度 (Alpha)，15px 是扩散范围 */
    filter: drop-shadow(0px 6px 15px rgba(100, 184, 255, 0.35)) !important;
    -webkit-filter: drop-shadow(0px 6px 15px rgba(100, 184, 255, 0.35)) !important;
    transform: translateZ(0); 
    transition: filter 0.3s ease;
}

/* 鼠标悬停时发光增强 */
img:hover {
    filter: drop-shadow(0px 8px 20px rgba(100, 184, 255, 1.0)) !important;
    -webkit-filter: drop-shadow(0px 8px 20px rgba(100, 184, 255, 1.0)) !important;
}

/* 侧边栏内的圆形头像框内的图标阴影微调（稍微收敛一点） */
[data-testid="stSidebar"] img {
    filter: drop-shadow(2px 4px 10px rgba(100, 184, 255, 0.6)) !important;
    -webkit-filter: drop-shadow(2px 4px 10px rgba(100, 184, 255, 0.6)) !important;
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
    min-height: 150px !important;
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
Icon=get_base64("OptimaxScan Icon.png")
upload=get_base64("Upload.png")

# --- 📍 3. 注入原始脚本的核心功能内核 ---

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
    canvas.save(output, format="JPEG", quality=q)
    while output.tell() / 1024 > 450 and q > 20:
        q -= 5
        output = io.BytesIO()
        canvas.save(output, format="JPEG", quality=q)
    return output.getvalue()

def process_scan_layered_from_mem(pil_img, is_small):
    """Optimax Scan Engine v2 核心算法"""

    pil_img = ImageOps.exif_transpose(pil_img)
    pil_img.thumbnail((2000,2000), Image.Resampling.BILINEAR)

    img_cv = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)

    if is_small:

        smooth = cv2.GaussianBlur(gray, (3, 3), 0)
        bg = cv2.medianBlur(smooth, 31)

        final = cv2.divide(smooth, bg, scale=245)

        clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(12, 12))
        final = clahe.apply(final)

        final = cv2.fastNlMeansDenoising(
            final, None,
            h=10,
            templateWindowSize=7,
            searchWindowSize=15
        )

        _, white_bg_mask = cv2.threshold(final, 220, 255, cv2.THRESH_BINARY)
        final[white_bg_mask == 255] = 255

        gaussian_blur = cv2.GaussianBlur(final, (0, 0), 1.5)
        final = cv2.addWeighted(final, 1.22, gaussian_blur, -0.22, 0)

    else:

        _, black_mask = cv2.threshold(gray, 70, 255, cv2.THRESH_BINARY_INV)

        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
            black_mask, connectivity=8
        )

        valid_black_mask = np.zeros_like(black_mask)

        for i in range(1, num_labels):
            if stats[i, cv2.CC_STAT_AREA] < 2500:
                valid_black_mask[labels == i] = 255

        bg = cv2.medianBlur(gray, 51)
        diff = cv2.divide(gray, bg, scale=255)

        clahe = cv2.createCLAHE(clipLimit=1.2, tileGridSize=(8, 8))
        enhanced = clahe.apply(diff)

        res = cv2.adaptiveThreshold(
            enhanced, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            51, 20
        )

        final = cv2.addWeighted(enhanced, 0.75, res, 0.25, 0)
        final[valid_black_mask == 255] = 0
        final = cv2.medianBlur(final, 3)
        final = cv2.fastNlMeansDenoising(
            final, None,
            h=12,
            templateWindowSize=7,
            searchWindowSize=21
        )

        _, white_bg_mask = cv2.threshold(final, 235, 255, cv2.THRESH_BINARY)
        final[white_bg_mask == 255] = 255

        gaussian_blur = cv2.GaussianBlur(final, (0, 0), 2.2)
        final = cv2.addWeighted(final, 1.35, gaussian_blur, -0.35, 0)

    return Image.fromarray(cv2.cvtColor(final, cv2.COLOR_GRAY2RGB))

# --- 📍 4. 进度条动画 ---
st.markdown("""
<style>
/* --- 进度条流动与流光核 --- */
[data-testid="stProgressBar"] > div > div {
    transition: width 1.8s cubic-bezier(0.4, 0, 0.2, 1) !important;
}
div[data-testid="stProgressBar"]{
    margin-left:5% !important;
    width:9% !important;
    position:relative;
    overflow:hidden;
}

.stProgress > div > div { 
    background-color: transparent !important; 
    border-radius: 10px !important; 
    height: 6px !important;
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

# --- 📍 5. 侧边栏 ---
st.markdown("""
<style>
/* 侧边栏基础拟态 */
[data-testid="stSidebar"] {
    background-color: #F0F4F8 !important;
    box-shadow: inset -10px 0 20px #d1d9e6 !important;
    border: none !important;
}

/* 和Home Page的方框对齐：消除侧边栏顶部默认间距并上移整体内容 */
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
    padding-top: 0 !important;
    margin-top: -6.3px !important;

/* 侧边栏卡片：保持和主界面一致的凸起感 */
.sidebar-card {
    background: #F0F4F8;
    border-radius: 20px;
    padding: 63px 20px 25px 20px;
    margin: 15px;
    box-shadow: 6px 6px 12px #d1d9e6, -6px -6px 12px #ffffff;
    color: #64B8FF;
    font-weight: 600;
    text-align: center;
    margin-bottom: -10px;
}
</style>
""", unsafe_allow_html=True)

with st.sidebar:
# --- Icon Header ---
    st.markdown(f'''
        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; margin-bottom: -65px; padding-top: 20px; position: relative; z-index: 99;">
            <div style="
                width: 97px; height: 97px; border-radius: 50%; 
                background: #F0F4F8; display: flex; align-items: center; justify-content: center;
                box-shadow: 6px 6px 12px #d1d9e6, -6px -6px 12px #ffffff;
            ">
                <div style="
                    width: 87px; height: 87px; border-radius: 50%;
                    background: #F0F4F8; display: flex; align-items: center; justify-content: center;
                    box-shadow: inset 4px 4px 8px #d1d9e6, inset -4px -4px 8px #ffffff;
                    border: 1px solid rgba(255,255,255,0.9);
                ">
                <img src="data:image/png;base64,{Icon}" style="width: 55px;">
            </div>
        </div>
    ''', unsafe_allow_html=True)
    
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
    ''', unsafe_allow_html=True)

    # --- 第二组: TUTORIAL ---
    st.markdown(f'''
        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; margin-bottom: -65px; margin-top: 30px; padding-top: 20px; position: relative; z-index: 99;">
            <div style="
                width: 97px; height: 97px; border-radius: 50%; 
                background: #F0F4F8; display: flex; align-items: center; justify-content: center;
                box-shadow: 6px 6px 12px #d1d9e6, -6px -6px 12px #ffffff;
            ">
                <div style="
                    width: 87px; height: 87px; border-radius: 50%;
                    background: #F0F4F8; display: flex; align-items: center; justify-content: center;
                    box-shadow: inset 4px 4px 8px #d1d9e6, inset -4px -4px 8px #ffffff;
                    border: 1px solid rgba(255,255,255,0.9);
                 ">
                <img src="data:image/png;base64,{upload}" style="width: 55px;">
            </div>
        </div>
        ''', unsafe_allow_html=True)
    
    st.markdown('''
    <div class="sidebar-card">
        <div style="text-align: center; font-size: 1.1em; color: #64B8FF; font-weight: 600; margin-bottom: 7px">
            上传步骤 | TUTORIAL
        </div>
        <div style="text-align: left; font-size: 0.9em; color: #A0AEC0; font-weight: 400; line-height: 1.6; letter-spacing: 0.25px; margin-left: 14px">
            1. 上传素材 | Upload Files<br>
        </div>
        <div style="text-align: left; font-size: 0.9em; color: #A0AEC0; font-weight: 400; line-height: 1.6; letter-spacing: -0.05px; margin-left: 14px">
            2. 开始优化 | Start Refining
        </div>
            <div style="text-align: left; font-size: 0.7em; color: #A0AEC0; font-weight: 400; line-height: 1.6; letter-spacing: 0.7px; margin-left: 28px">
            分析: 智能修复光线/清晰度<br>
            Auto-Fix Light and Clarity<br>
            压缩: 体积优化，画质无损<br>
            Lossless Size Optimization<br>
            排版: 统一 Letter Size 布局<br>
            Standard 8.5 × 11 Layout
        </div>
        <div style="text-align: left; font-size: 0.9em; color: #A0AEC0; font-weight: 400; line-height: 1.6; margin-left: 14px">  
            3. 保存黑白 | Export B&W
        </div>
    </div>
    ''', unsafe_allow_html=True)

# --- 📍 6. 业务逻辑 ---

st.markdown("""
<div class="title-card">
<div class="main-title">OPTIMAX SCAN</div>
<div class="sub-title">Analog Essence • Digital Precision</div>
</div>
""",unsafe_allow_html=True)

uploaded_files=st.file_uploader("",accept_multiple_files=True,label_visibility="collapsed")
visual_progress = 0

if uploaded_files:
    st.markdown(
f'<div class="queued-title" style="visibility:hidden;height:0;margin:0;padding:0;"><img src="data:image/png;base64,{folder}" style="height:0;"> 待优化素材 | QUEUED</div>',
unsafe_allow_html=True
)
    
# 🔻——— 父容器 ———🔻
    st.markdown(f'<div style="position:relative;z-index:10;width:100%;height:100px;pointer-events:none;"><div style="position:absolute;bottom:2px;left:5%;width:90%;height:6px;background:#d1d9e6;border-radius:10px;box-shadow:inset 2px 2px 4px #b8bec8,inset -2px -2px 4px #eef1f5;"></div><div style="position:absolute;top:60%;left:50%;transform:translate(-50%,-50%);display:flex;align-items:center;gap:10px;"><img src="data:image/png;base64,{star}" style="width:25px;"><span style="color:#64B8FF;font-weight:600;">开始优化 | START REFINING</span></div></div>', unsafe_allow_html=True)
# 🔺---🔺

# 🔻——— 物品4 Button ———🔻
    st.markdown('<style>div[data-testid="stVerticalBlock"] > div:has(div.stButton){margin-top:-100px !important;position:relative !important;z-index:1 !important;}</style>', unsafe_allow_html=True)
    if st.button(" ", use_container_width=True, key="refine_btn"):
    # 🔺-----------------------------------------------------------------------🔺
        all_processed_bytes = []
        # 🔻——— 物品2 进度条（渲染在按钮下方，用CSS拉回凹槽位置）———🔻
        st.markdown('<style>div[data-testid="stVerticalBlock"] > div:has(div[data-testid="stProgressBar"]){margin-top:-80px !important;margin-bottom:80px !important;position:relative !important;z-index:5 !important;pointer-events:none !important;}</style>', unsafe_allow_html=True)
        progress_bar = st.progress(0.01)
        visual_progress = 0.01
        # 🔺-------------------------------------------------------------------🔺

        def smooth_progress(target, duration=0.4):
            global visual_progress
            if target <= visual_progress:
                return
            steps = 12
            step = (target - visual_progress) / steps
            for _ in range(steps):
                visual_progress += step
                progress_bar.progress(min(visual_progress, 0.99))
                time.sleep(duration / steps)
        
        total_files = len(uploaded_files)
        
        for file_idx, file in enumerate(uploaded_files):
            # 计算当前文件在总进度中的基础占比和每份份额
            file_base_pct = file_idx / total_files
            file_chunk_pct = 1.0 / total_files
            
            file_bytes = file.read()
            file_size_kb = len(file_bytes) / 1024
            
            temp_images = []
            if file.name.lower().endswith('.pdf'):
                try:
                    smooth_progress(min(file_base_pct + file_chunk_pct * 0.2, 0.99), duration=0.3)
                    pages = convert_from_bytes(file_bytes)
                    temp_images.extend(pages)
                except: continue
            else:
                img = Image.open(io.BytesIO(file_bytes))
                img = ImageOps.exif_transpose(img)
                if img.mode != "RGB":
                    img = img.convert("RGB")
                pil_img = img
                pil_img.thumbnail((3000,3000), Image.Resampling.BILINEAR)
                temp_images.append(pil_img)
            
            num_pages = len(temp_images)
            if num_pages == 0: continue
            
            for page_idx, pil_img in enumerate(temp_images):
                page_base = file_base_pct + (page_idx / num_pages) * file_chunk_pct
                page_chunk = file_chunk_pct / num_pages
                status = get_image_status(pil_img, file_size_kb)
                
                if status == "KEEP_FILE":
                    # --- [快车道] 小文件/原生文件：直接完成，不拉慢 ---
                    page_bytes = process_and_compress_to_letter(pil_img)
                else:
                    smooth_progress(min(page_base + page_chunk * 0.25, 0.99))
                        
                    # OpenCV 核心处理
                    processed_img = process_scan_layered_from_mem(pil_img, file_size_kb < 200)

                    # --- 收尾 ---
                    smooth_progress(min(page_base + page_chunk * 0.55, 0.99))
                    page_bytes = process_and_compress_to_letter(processed_img)
                    smooth_progress(min(page_base + page_chunk * 0.85, 0.99))
                    
                all_processed_bytes.append(page_bytes)

        st.markdown(f'''<div class="status-text fade-in-up" style="display:flex;align-items:center;letter-spacing:-0.35px;"><img src="data:image/png;base64,{check_mark}" style="width:22px;margin-right:8px;">处理完成 | TASKS COMPLETE</div>''', unsafe_allow_html=True)
        st.markdown(f'''<div class="fade-in-up" style="display:flex;align-items:center;justify-content:center;height:90px;pointer-events:none;position:relative;z-index:10;"><img src="data:image/png;base64,{download}" style="width:25px;margin-right:10px;"><span style="color:#64B8FF;font-weight:600;">保存文件 | DOWNLOAD PDF</span></div>''', unsafe_allow_html=True)
        st.markdown('<style>div.stDownloadButton { margin-top:-92px !important; }</style>',unsafe_allow_html=True)

        final_pdf = img2pdf.convert(all_processed_bytes)
        st.download_button(
            label=" ",
            data=final_pdf,
            file_name="optimax_processed.pdf",
            mime="application/pdf",
            use_container_width=True,
            key="download_pdf"
        )

        st.markdown('<div id="download_anchor"></div>', unsafe_allow_html=True)
        
        # 【最终节点】收尾至完美的 100%
        progress_bar.progress(1.0)

        # 自动滚动到底部
        components.html("""
        <script>
        setTimeout(function() {
            const el = window.parent.document.getElementById("download_anchor");
            if (el){
                el.scrollIntoView({
                    behavior: "smooth",
                    block: "center"
                });
            }
        }, 700);
        </script>
        """, height=0)

# --- 📍 7. Footnotes ---

st.markdown('<div class="footer">Optimax Scan Engine v2.0 | © 2026 Jerry Yin</div>',unsafe_allow_html=True)
