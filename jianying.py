import json
import logging
import shutil
import subprocess
import time
import uuid
from dataclasses import field
from pathlib import Path
from typing import List, Union, Any, Optional

import pyautogui
import pyperclip
from clicknium import clicknium as cc, ui, locator
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, stop_after_delay, wait_fixed

from pyext.commons import UUID, ProcessManager, IntRange
from pyext.io import JsonFile, Directory, GitRepository

logger = logging.getLogger(__name__)


class TimeRange(BaseModel):
    """
    表示一个时间范围
    """

    duration: Optional[int] = None
    """持续时间"""

    start: Optional[int] = None
    """开始时间"""


class ImageMaterial(BaseModel):
    """
    图片素材
    """

    create_time: Optional[int] = None
    """创建时间,Unix时间戳"""
    duration: Optional[int] = None
    """持续时间,以微秒为单位"""

    extra_info: Optional[str] = None
    """额外信息,例如文件名"""

    file_Path: Optional[str] = None
    """文件路径"""

    height: Optional[int] = None
    """图片高度,以像素为单位"""

    id: Optional[str] = None
    """图片素材的唯一标识符"""

    import_time: Optional[int] = None
    """导入时间,Unix时间戳"""

    import_time_ms: Optional[int] = None
    """导入时间,以微秒为单位"""

    item_source: Optional[str] = None
    """素材来源"""

    md5: Optional[str] = None
    """文件的MD5哈希值,用于校验"""

    metetype: Optional[str] = None
    """素材类型,例如 "photo" """

    roughcut_time_range: Optional[TimeRange] = None
    """粗剪时间范围"""

    sub_time_range: Optional[TimeRange] = None
    """子时间范围"""

    type: Optional[int] = None
    """类型,例如`0`代表图片素材"""

    width: Optional[int] = None
    """图片宽度,以像素为单位"""


class DraftMaterial(BaseModel):
    """
    表示草稿中的一个素材
    """

    type: Optional[int] = None
    """素材类型"""

    value: Optional[List[Union[ImageMaterial]]] = None
    """素材列表"""


class DraftEnterpriseInfo(BaseModel):
    """
    企业信息
    """

    draft_enterprise_extra: Optional[str] = None
    """企业额外信息"""

    draft_enterprise_id: Optional[str] = None
    """企业ID"""

    draft_enterprise_name: Optional[str] = None
    """企业名称"""

    enterprise_material: Optional[List] = None
    """企业材料"""


class DraftMetaInfo(BaseModel):
    """
    草稿元信息
    """

    cloud_package_completed_time: Optional[str] = None
    """云端包完成时间"""

    draft_cloud_capcut_purchase_info: Optional[str] = None
    """云端Capcut购买信息"""

    draft_cloud_last_action_download: Optional[bool] = None
    """云端最后动作是否为下载"""

    draft_cloud_materials: List = field(default_factory=list)
    """云端材料"""

    draft_cloud_purchase_info: Optional[str] = None
    """云端购买信息"""

    draft_cloud_template_id: Optional[str] = None
    """云端模板ID"""

    draft_cloud_tutorial_info: Optional[str] = None
    """云端教程信息"""

    draft_cloud_videocut_purchase_info: Optional[str] = None
    """云端视频剪辑购买信息"""

    draft_cover: str = "draft_cover.jpg"
    """草稿封面"""

    draft_deeplink_url: Optional[str] = None
    """草稿深度链接URL"""

    draft_enterprise_info: DraftEnterpriseInfo = field(default_factory=DraftEnterpriseInfo)
    """企业信息"""

    draft_fold_path: str = None
    """草稿文件夹路径"""

    draft_id: str = UUID.random(upper=True, formats=[(8, '-'), (12, '-'), (16, '-'), (20, '-')])
    """草稿ID"""

    draft_is_ai_packaging_used: bool = False
    """是否使用AI打包"""

    draft_is_ai_shorts: bool = False
    """是否为AI短视频"""

    draft_is_ai_translate: bool = False
    """是否使用AI翻译"""

    draft_is_article_video_draft: bool = False
    """是否为文章视频草稿"""

    draft_is_from_deeplink: str = "false"
    """是否来自深度链接"""

    draft_is_invisible: bool = False
    """是否为隐形草稿"""

    draft_materials: List[DraftMaterial] = field(default_factory=list)
    """草稿素材"""

    draft_materials_copied_info: List = field(default_factory=list)
    """复制的草稿材料信息"""

    draft_name: str = None
    """草稿名称"""

    draft_new_version: str = ""
    """草稿新版本"""

    draft_removable_storage_device: str = "D:"
    """可移动存储设备"""

    draft_root_path: str = None
    """草稿根路径"""

    draft_segment_extra_info: List = field(default_factory=list)
    """草稿段落额外信息"""

    draft_timeline_materials_size_: int = 8016
    """时间线材料大小"""

    draft_type: str = ""
    """草稿类型"""

    tm_draft_cloud_completed: str = ""
    """草稿云端完成时间"""

    tm_draft_cloud_modified: int = 0
    """草稿云端修改时间"""

    tm_draft_create: int = 1720784146489727
    """草稿创建时间"""

    tm_draft_modified: int = 1720785106585349
    """草稿修改时间"""

    tm_draft_removed: int = 0
    """草稿移除时间"""

    tm_duration: int = 0
    """持续时间"""


class Type0Value(BaseModel):
    creation_time: int
    """创建时间"""

    display_name: Optional[str]
    """显示名称"""

    filter_type: int
    """过滤类型"""

    id: Optional[str]
    """ID"""

    import_time: int
    """导入时间"""

    import_time_us: int
    """导入时间（微秒）"""

    sort_sub_type: int
    """排序子类型"""

    sort_type: int
    """排序类型"""


class Type1Value(BaseModel):
    child_id: str
    """子ID"""

    parent_id: str
    """父ID"""


class DraftVirtualStoreItem(BaseModel):
    """
    草稿虚拟存储中的一个条目
    """

    type: int
    """类型"""

    value: List[Union[Type0Value, Type1Value]]
    """值"""


class DraftVirtualStore(BaseModel):
    draft_materials: List[DraftMaterial] = field(default_factory=list)
    """草稿材料"""

    draft_virtual_store: List[DraftVirtualStoreItem] = field(default_factory=list)
    """虚拟存储"""


# region draft_content.json

class CanvasConfig(BaseModel):
    height: int
    """画布高度"""

    ratio: str
    """画布比例"""

    width: int
    """画布宽度"""


class Platform(BaseModel):
    app_id: int = 3704
    """应用ID"""

    app_source: str = "lv"
    """应用来源"""

    app_version: str = "5.9.0"
    """应用版本"""

    device_id: str = "93c3be64246ff28979c8f97ecb5e96a9"
    """设备ID"""

    hard_disk_id: str = "95fde6ca35187cfd091c19dae20a7c86"
    """硬盘ID"""

    mac_address: str = "1f9453637d15522c8f952a03aefa9e74,d04e333df6159c278b5e57296362720e"
    """MAC地址"""

    os: str = "windows"
    """操作系统"""

    os_version: str = "10.0.22631"
    """操作系统版本"""


class Keyframes(BaseModel):
    adjusts: List = field(default_factory=list)
    """调整"""

    audios: List = field(default_factory=list)
    """音频"""

    effects: List = field(default_factory=list)
    """效果"""

    filters: List = field(default_factory=list)
    """滤镜"""

    handwrites: List = field(default_factory=list)
    """手写"""

    stickers: List = field(default_factory=list)
    """贴纸"""

    texts: List = field(default_factory=list)
    """文本"""

    videos: List = field(default_factory=list)
    """视频"""


class Canvas(BaseModel):
    album_image: str = ""
    """专辑图像"""

    blur: float = 0.0
    """模糊度"""

    color: str = ""
    """颜色"""

    id: str = field(
        default_factory=lambda: UUID.random(upper=True, formats=[(8, '-'), (12, '-'), (16, '-'), (20, '-')]))
    """ID"""

    image: str = ""
    """图像"""

    image_id: str = ""
    """图像ID"""

    image_name: str = ""
    """图像名称"""

    source_platform: int = 0
    """来源平台"""

    team_id: str = ""
    """团队ID"""

    type: str = "canvas_color"
    """类型"""


class AudioConfig(BaseModel):
    audio_channel_mapping: int = 0
    """音频通道映射"""

    id: str = field(
        default_factory=lambda: UUID.random(upper=True, formats=[(8, '-'), (12, '-'), (16, '-'), (20, '-')]))
    """ID"""

    is_config_open: bool = False
    """配置是否开启"""

    type: str = "none"
    """类型"""


class SpeedConfig(BaseModel):
    curve_speed: Optional[float] = None
    """曲线速度"""

    id: str = field(
        default_factory=lambda: UUID.random(upper=True, formats=[(8, '-'), (12, '-'), (16, '-'), (20, '-')]))
    """ID"""

    mode: int = 0
    """模式"""

    speed: float = 1.0
    """速度"""

    type: str = "speed"
    """类型"""


class Crop(BaseModel):
    lower_left_x: float = 0.0
    """左下角X坐标"""

    lower_left_y: float = 1.0
    """左下角Y坐标"""

    lower_right_x: float = 1.0
    """右下角X坐标"""

    lower_right_y: float = 1.0
    """右下角Y坐标"""

    upper_left_x: float = 0.0
    """左上角X坐标"""

    upper_left_y: float = 0.0
    """左上角Y坐标"""

    upper_right_x: float = 1.0
    """右上角X坐标"""

    upper_right_y: float = 0.0
    """右上角Y坐标"""


class Matting(BaseModel):
    flag: int = 0
    """标志"""

    has_use_quick_brush: bool = False
    """是否使用快速刷"""

    has_use_quick_eraser: bool = False
    """是否使用快速橡皮擦"""

    interactiveTime: List[int] = ()
    """交互时间"""

    path: str = ""
    """路径"""

    strokes: List[str] = ()
    """笔触"""


class Stable(BaseModel):
    matrix_path: str = ""
    """矩阵路径"""

    stable_level: int = 0
    """稳定等级"""

    time_range: TimeRange = field(default_factory=TimeRange)
    """时间范围"""


class VideoAlgorithm(BaseModel):
    algorithms: List[str] = ()
    """算法"""

    complement_frame_config: Optional[str] = None
    """补帧配置"""

    deflicker: Optional[str] = None
    """去闪烁"""

    gameplay_configs: List[str] = ()
    """游戏配置"""

    motion_blur_config: Optional[str] = None
    """运动模糊配置"""

    noise_reduction: Optional[str] = None
    """降噪"""

    path: str = ""
    """路径"""

    quality_enhance: Optional[str] = None
    """质量增强"""

    time_range: Optional[TimeRange] = None
    """时间范围"""


class Photo(BaseModel):
    aigc_type: str = "none"
    """AIGC类型"""

    audio_fade: Optional[float] = None
    """音频淡入淡出"""

    cartoon_path: str = ""
    """卡通路径"""

    category_id: str = ""
    """类别ID"""

    category_name: str = "local"
    """类别名称"""

    check_flag: int = 63487
    """检查标志"""

    crop: Crop = field(default_factory=Crop)
    """裁剪"""

    crop_ratio: str = "free"
    """裁剪比例"""

    crop_scale: float = 1.0
    """裁剪比例"""

    duration: int = 10800000000
    """持续时间"""

    extra_type_option: int = 0
    """额外类型选项"""

    formula_id: str = ""
    """公式ID"""

    freeze: Optional[float] = None
    """冻结"""

    has_audio: bool = False
    """是否有音频"""

    height: int = 1536
    """高度"""

    id: str = field(
        default_factory=lambda: UUID.random(upper=True, formats=[(8, '-'), (12, '-'), (16, '-'), (20, '-')]))
    """ID"""

    intensifies_audio_path: str = ""
    """强化音频路径"""

    intensifies_path: str = ""
    """强化路径"""

    is_ai_generate_content: bool = False
    """是否是AI生成内容"""

    is_copyright: bool = False
    """是否有版权"""

    is_text_edit_overdub: bool = False
    """是否文本编辑配音"""

    is_unified_beauty_mode: bool = False
    """是否统一美颜模式"""

    local_id: str = ""
    """本地ID"""

    local_material_id: str = ""
    """本地素材ID"""

    material_id: str = ""
    """素材ID"""

    material_name: str = ""
    """素材名称"""

    material_url: str = ""
    """素材URL"""

    matting: Matting = field(default_factory=Matting)
    """抠图"""

    media_path: str = ""
    """媒体路径"""

    object_locked: Optional[bool] = None
    """对象锁定"""

    origin_material_id: str = ""
    """原始素材ID"""

    path: str = ""
    """路径"""

    picture_from: str = "none"
    """图片来源"""

    picture_set_category_id: str = ""
    """图片集类别ID"""

    picture_set_category_name: str = ""
    """图片集类别名称"""

    request_id: str = ""
    """请求ID"""

    reverse_intensifies_path: str = ""
    """反向强化路径"""

    reverse_path: str = ""
    """反向路径"""

    smart_motion: Optional[float] = None
    """智能运动"""

    source: int = 0
    """来源"""

    source_platform: int = 0
    """来源平台"""

    stable: Stable = field(default_factory=Stable)
    """稳定"""

    team_id: str = ""
    """团队ID"""

    type: str = "photo"
    """类型"""

    video_algorithm: VideoAlgorithm = field(default_factory=VideoAlgorithm)
    """视频算法"""

    width: int = 1024
    """宽度"""


class VocalSeparation(BaseModel):
    choice: int = 0
    """选择"""

    id: str = field(
        default_factory=lambda: UUID.random(upper=True, formats=[(8, '-'), (12, '-'), (16, '-'), (20, '-')]))
    """ID"""

    production_path: str = ""
    """制作路径"""

    time_range: Optional[TimeRange] = None
    """时间范围"""

    type: str = "vocal_separation"
    """类型"""


class Flip(BaseModel):
    horizontal: bool = False
    """水平翻转"""

    vertical: bool = False
    """垂直翻转"""


class Scale(BaseModel):
    x: float = 1.0
    """x轴缩放"""

    y: float = 1.0
    """y轴缩放"""


class Transform(BaseModel):
    x: float = 0.0
    """x轴变换"""

    y: float = 0.0
    """y轴变换"""


class Clip(BaseModel):
    alpha: float = 1.0
    """透明度"""

    flip: Flip = field(default_factory=Flip)
    """翻转"""

    rotation: float = 0.0
    """旋转"""

    scale: Scale = field(default_factory=Scale)
    """缩放"""

    transform: Transform = field(default_factory=Transform)
    """变换"""


class HDRSettings(BaseModel):
    intensity: float = 1.0
    """强度"""

    mode: int = 1
    """模式"""

    nits: int = 1000
    """尼特"""


class ResponsiveLayout(BaseModel):
    enable: bool = False
    """启用"""

    horizontal_pos_layout: int = 0
    """水平位置布局"""

    size_layout: int = 0
    """大小布局"""

    target_follow: str = ""
    """目标跟随"""

    vertical_pos_layout: int = 0
    """垂直位置布局"""


class UniformScale(BaseModel):
    on: bool = True
    """启用"""

    value: float = 1.0
    """值"""


class Segment(BaseModel):
    caption_info: Optional[str] = None
    """字幕信息"""

    cartoon: bool = False
    """卡通"""

    clip: Clip = field(default_factory=Clip)
    """剪辑"""

    common_keyframes: List[str] = ()
    """常见关键帧"""

    enable_adjust: bool = True
    """启用调整"""

    enable_color_correct_adjust: bool = False
    """启用颜色校正调整"""

    enable_color_curves: bool = True
    """启用颜色曲线"""

    enable_color_match_adjust: bool = False
    """启用颜色匹配调整"""

    enable_color_wheels: bool = True
    """启用颜色轮"""

    enable_lut: bool = True
    """启用LUT"""

    enable_smart_color_adjust: bool = False
    """启用智能颜色调整"""

    extra_material_refs: List[str] = field(default_factory=list)
    """额外素材引用"""

    group_id: str = ""
    """组ID"""

    hdr_settings: Optional[HDRSettings] = field(default_factory=HDRSettings)
    """HDR设置"""

    id: str = field(
        default_factory=lambda: UUID.random(upper=True, formats=[(8, '-'), (12, '-'), (16, '-'), (20, '-')]))
    """ID"""

    intensifies_audio: bool = False
    """强化音频"""

    is_placeholder: bool = False
    """是否占位符"""

    is_tone_modify: bool = False
    """是否音调修改"""

    keyframe_refs: List[str] = ()
    """关键帧引用"""

    last_nonzero_volume: float = 1.0
    """最后一个非零音量"""

    material_id: str = None
    """素材ID"""

    render_index: int = 0
    """渲染索引"""

    responsive_layout: ResponsiveLayout = field(default_factory=ResponsiveLayout)
    """响应布局"""

    reverse: bool = False
    """反向"""

    source_timerange: Optional[TimeRange] = field(default_factory=TimeRange)
    """源时间范围"""

    speed: float = 1.0
    """速度"""

    target_timerange: TimeRange = field(default_factory=TimeRange)
    """目标时间范围"""

    template_id: str = ""
    """模板ID"""

    template_scene: str = "default"
    """模板场景"""

    track_attribute: int = 0
    """轨道属性"""

    track_render_index: int = 0
    """轨道渲染索引"""

    uniform_scale: UniformScale = field(default_factory=UniformScale)
    """统一缩放"""

    visible: bool = True
    """可见性"""

    volume: float = 1.0
    """音量"""


class Track(BaseModel):
    attribute: int = 0
    """属性"""

    flag: int = 0
    """标志"""

    id: str = field(
        default_factory=lambda: UUID.random(upper=True, formats=[(8, '-'), (12, '-'), (16, '-'), (20, '-')]))
    """ID"""

    is_default_name: bool = True
    """是否默认名称"""

    name: str = ""
    """名称"""

    segments: List[Segment] = field(default_factory=list)
    """片段"""

    type: str = "video"
    """类型"""


class StickerAnimation(BaseModel):
    animations: List[str] = field(default_factory=list)
    """动画"""

    id: str = field(
        default_factory=lambda: UUID.random(upper=True, formats=[(8, '-'), (12, '-'), (16, '-'), (20, '-')]))
    """ID"""

    multi_language_current: str = "none"
    """多语言当前状态"""

    type: str = "sticker_animation"
    """类型"""


class CaptionTemplateInfo(BaseModel):
    category_id: str = ""
    """分类ID"""

    category_name: str = ""
    """分类名称"""

    effect_id: str = ""
    """效果ID"""

    is_new: bool = False
    """是否新建"""

    path: str = ""
    """路径"""

    request_id: str = ""
    """请求ID"""

    resource_id: str = ""
    """资源ID"""

    resource_name: str = ""
    """资源名称"""

    source_platform: int = 0
    """来源平台"""


class ComboInfo(BaseModel):
    text_templates: List[str] = field(default_factory=list)
    """文本模板"""


class ShadowPoint(BaseModel):
    x: float = 0.6363961030678928
    """x轴阴影点"""

    y: float = -0.6363961030678928
    """y轴阴影点"""


class Words(BaseModel):
    end_time: List[str] = field(default_factory=list)
    """结束时间"""

    start_time: List[str] = field(default_factory=list)
    """开始时间"""

    text: List[str] = field(default_factory=list)
    """文本"""


class Solid(BaseModel):
    alpha: float = None
    """透明度"""

    color: List[int] = (1, 1, 1)
    """颜色"""


class Content(BaseModel):
    render_type: str = None
    """渲染类型"""

    solid: Solid = field(default_factory=Solid)
    """实心"""


class Fill(BaseModel):
    alpha: Optional[float] = None
    """透明度"""

    content: Optional[Content] = field(default_factory=Content)
    """内容"""

    width: Optional[float] = None
    """宽度"""


class Font(BaseModel):
    id: str = ""
    """字体ID"""

    path: str = "D:/Program Files/JianyingPro5.9.0/5.9.0.11632/Resources/Font/SystemFont/zh-hans.ttf"
    """字体路径"""


class Style(BaseModel):
    fill: Fill = field(default_factory=Fill)
    """填充"""

    font: Font = field(default_factory=Font)
    """字体"""

    range: List[int] = (0, 4)
    """范围"""

    size: float = 15.0
    """大小"""

    strokes: Optional[List[Fill]] = None
    """笔触"""

    useLetterColor: bool = None
    """使用字母颜色"""


class TextContent(BaseModel):
    styles: List[Style] = field(default_factory=list)
    """样式"""

    text: str = "默认文本"
    """文本"""


class TextMaterial(BaseModel):
    add_type: int = 0
    """添加类型"""

    alignment: int = 1
    """对齐"""

    background_alpha: float = 1.0
    """背景透明度"""

    background_color: str = ""
    """背景颜色"""

    background_height: float = 0.14
    """背景高度"""

    background_horizontal_offset: float = 0.0
    """背景水平偏移"""

    background_round_radius: float = 0.0
    """背景圆角半径"""

    background_style: int = 0
    """背景样式"""

    background_vertical_offset: float = 0.0
    """背景垂直偏移"""

    background_width: float = 0.14
    """背景宽度"""

    base_content: str = ""
    """基础内容"""

    bold_width: float = 0.0
    """粗体宽度"""

    border_alpha: float = 1.0
    """边框透明度"""

    border_color: str = ""
    """边框颜色"""

    border_width: float = 0.08
    """边框宽度"""

    caption_template_info: CaptionTemplateInfo = field(default_factory=CaptionTemplateInfo)
    """字幕模板信息"""

    check_flag: int = 7
    """检查标志"""

    combo_info: ComboInfo = field(default_factory=ComboInfo)
    """组合信息"""

    content: str = "{\"styles\":[{\"fill\":{\"alpha\":1.0,\"content\":{\"render_type\":\"solid\",\"solid\":{\"alpha\":1.0,\"color\":[1.0,1.0,1.0]}}},\"font\":{\"id\":\"\",\"path\":\"D:/Program Files/JianyingPro5.9.0/5.9.0.11632/Resources/Font/SystemFont/zh-hans.ttf\"},\"range\":[0,4],\"size\":15.0}],\"text\":\"默认文本\"}"
    """内容,TextContent类的json字符串"""

    fixed_height: float = -1.0
    """固定高度"""

    fixed_width: float = -1.0
    """固定宽度"""

    font_category_id: str = ""
    """字体分类ID"""

    font_category_name: str = ""
    """字体分类名称"""

    font_id: str = ""
    """字体ID"""

    font_name: str = ""
    """字体名称"""

    font_path: str = "D:/Program Files/JianyingPro5.9.0/5.9.0.11632/Resources/Font/SystemFont/zh-hans.ttf"
    """字体路径"""

    font_resource_id: str = ""
    """字体资源ID"""

    font_size: float = None
    """字体大小"""

    font_source_platform: int = 0
    """字体来源平台"""

    font_team_id: str = ""
    """字体团队ID"""

    font_title: str = "none"
    """字体标题"""

    font_url: str = ""
    """字体URL"""

    fonts: List[str] = ()
    """字体"""

    force_apply_line_max_width: bool = False
    """强制应用行最大宽度"""

    global_alpha: float = 1.0
    """全局透明度"""

    group_id: str = ""
    """组ID"""

    has_shadow: bool = False
    """有阴影"""

    id: str = field(
        default_factory=lambda: UUID.random(upper=True, formats=[(8, '-'), (12, '-'), (16, '-'), (20, '-')]))
    """ID"""

    initial_scale: float = 1.0
    """初始缩放"""

    inner_padding: float = -1.0
    """内部填充"""

    is_rich_text: bool = False
    """是否富文本"""

    italic_degree: int = 0
    """斜体角度"""

    ktv_color: str = ""
    """KTV颜色"""

    language: str = ""
    """语言"""

    layer_weight: int = 1
    """层权重"""

    letter_spacing: float = 0.0
    """字母间距"""

    line_feed: int = 1
    """换行"""

    line_max_width: float = 0.82
    """行最大宽度"""

    line_spacing: float = 0.02
    """行间距"""

    multi_language_current: str = "none"
    """多语言当前状态"""

    name: str = ""
    """名称"""

    original_size: List[str] = ()
    """原始尺寸"""

    preset_category: str = ""
    """预设分类"""

    preset_category_id: str = ""
    """预设分类ID"""

    preset_has_set_alignment: bool = False
    """预设已设置对齐"""

    preset_id: str = ""
    """预设ID"""

    preset_index: int = 0
    """预设索引"""

    preset_name: str = ""
    """预设名称"""

    recognize_task_id: str = ""
    """识别任务ID"""

    recognize_type: int = 0
    """识别类型"""

    relevance_segment: List[str] = field(default_factory=list)
    """相关片段"""

    shadow_alpha: float = 0.9
    """阴影透明度"""

    shadow_angle: float = -45.0
    """阴影角度"""

    shadow_color: str = ""
    """阴影颜色"""

    shadow_distance: float = 5.0
    """阴影距离"""

    shadow_point: ShadowPoint = field(default_factory=ShadowPoint)
    """阴影点"""

    shadow_smoothing: float = 0.45
    """阴影平滑"""

    shape_clip_x: bool = False
    """形状剪辑X"""

    shape_clip_y: bool = False
    """形状剪辑Y"""

    source_from: str = ""
    """来源"""

    style_name: str = ""
    """样式名称"""

    sub_type: int = 0
    """子类型"""

    subtitle_keywords: Optional[str] = None
    """字幕关键词"""

    subtitle_template_original_fontsize: float = 0.0
    """字幕模板原始字体大小"""

    text_alpha: float = 1.0
    """文本透明度"""

    text_color: str = "#FFFFFF"
    """文本颜色"""

    text_curve: Optional[str] = None
    """文本曲线"""

    text_preset_resource_id: str = ""
    """文本预设资源ID"""

    text_size: int = 30
    """文本大小"""

    text_to_audio_ids: List[str] = field(default_factory=list)
    """文本到音频ID"""

    tts_auto_update: bool = False
    """TTS自动更新"""

    type: str = "text"
    """类型"""

    typesetting: int = 0
    """排版"""

    underline: bool = False
    """下划线"""

    underline_offset: float = 0.22
    """下划线偏移"""

    underline_width: float = 0.05
    """下划线宽度"""

    use_effect_default_color: bool = True
    """使用效果默认颜色"""

    words: Words = field(default_factory=Words)
    """单词"""


class TTSMeta(BaseModel):
    text: str
    """
    文本内容
    """
    text_seg_id: str
    """
    文本段ID
    """
    tts_path: str
    """
    TTS音频路径
    """
    tts_payload: str
    """
    TTS负载信息
    """
    tts_start: int
    """
    TTS开始时间
    """


class VideoMeta(BaseModel):
    path: str
    """
    视频路径
    """


class VoiceInfo(BaseModel):
    is_ai_clone_tone: bool
    """
    是否为AI克隆音调
    """
    is_ugc: bool
    """
    是否为UGC
    """
    resource_id: str
    """
    资源ID
    """
    speaker_id: str
    """
    说话者ID
    """
    speed: float
    """
    语速
    """
    tone_category_id: str
    """
    音调类别ID
    """
    tone_category_name: str
    """
    音调类别名称
    """
    tone_effect_id: str
    """
    音效ID
    """
    tone_effect_name: str
    """
    音效名称
    """
    tone_platform: str
    """
    音调平台
    """
    tone_second_category_id: str
    """
    音调二级类别ID
    """
    tone_second_category_name: str
    """
    音调二级类别名称
    """
    tone_type: str
    """
    音调类型
    """


class DigitalHuman(BaseModel):
    background: str
    """
    背景
    """
    digital_human_id: str
    """
    数字人ID
    """
    digital_human_source: str
    """
    数字人来源
    """
    entrance: str
    """
    入口
    """
    id: str
    """
    ID
    """
    local_task_id: str
    """
    本地任务ID
    """
    mask: str
    """
    遮罩
    """
    resource_id: str
    """
    资源ID
    """
    tts_metas: List[TTSMeta]
    """
    TTS元数据列表
    """
    type: str
    """
    类型
    """
    video_meta: VideoMeta
    """
    视频元数据
    """
    voice_info: VoiceInfo
    """
    语音信息
    """


class Materials(BaseModel):
    ai_translates: List = field(default_factory=list)
    """AI翻译"""

    audio_balances: List = field(default_factory=list)
    """音频平衡"""

    audio_effects: List = field(default_factory=list)
    """音频效果"""

    audio_fades: List = field(default_factory=list)
    """音频淡入淡出"""

    audio_track_indexes: List = field(default_factory=list)
    """音轨索引"""

    audios: List = field(default_factory=list)
    """音频"""

    beats: List = field(default_factory=list)
    """节拍"""

    canvases: List[Canvas] = field(default_factory=list)
    """画布"""

    chromas: List = field(default_factory=list)
    """色度"""

    color_curves: List = field(default_factory=list)
    """色彩曲线"""

    digital_humans: List[DigitalHuman] = field(default_factory=list)
    """数字人"""

    drafts: List = field(default_factory=list)
    """草稿"""

    effects: List = field(default_factory=list)
    """效果"""

    flowers: List = field(default_factory=list)
    """花朵"""

    green_screens: List = field(default_factory=list)
    """绿幕"""

    handwrites: List = field(default_factory=list)
    """手写"""

    hsl: List = field(default_factory=list)
    """色相饱和度亮度"""

    images: List = field(default_factory=list)
    """图片"""

    log_color_wheels: List = field(default_factory=list)
    """日志色轮"""

    loudnesses: List = field(default_factory=list)
    """响度"""

    manual_deformations: List = field(default_factory=list)
    """手动变形"""

    masks: List = field(default_factory=list)
    """遮罩"""

    material_animations: List[StickerAnimation] = field(default_factory=list)
    """材料动画"""

    material_colors: List = field(default_factory=list)
    """材料颜色"""

    multi_language_refs: List = field(default_factory=list)
    """多语言参考"""

    placeholders: List = field(default_factory=list)
    """占位符"""

    plugin_effects: List = field(default_factory=list)
    """插件效果"""

    primary_color_wheels: List = field(default_factory=list)
    """主色轮"""

    realtime_denoises: List = field(default_factory=list)
    """实时降噪"""

    shapes: List = field(default_factory=list)
    """形状"""

    smart_crops: List = field(default_factory=list)
    """智能裁剪"""

    smart_relights: List = field(default_factory=list)
    """智能光照"""

    sound_channel_mappings: List[AudioConfig] = field(default_factory=list)
    """声道映射"""

    speeds: List[SpeedConfig] = field(default_factory=list)
    """速度"""

    stickers: List = field(default_factory=list)
    """贴纸"""

    tail_leaders: List = field(default_factory=list)
    """片尾"""

    text_templates: List = field(default_factory=list)
    """文本模板"""

    texts: List[TextMaterial] = field(default_factory=list)
    """文本"""

    time_marks: List = field(default_factory=list)
    """时间标记"""

    transitions: List = field(default_factory=list)
    """转场"""

    video_effects: List = field(default_factory=list)
    """视频效果"""

    video_trackings: List = field(default_factory=list)
    """视频追踪"""

    videos: List[Union[Photo]] = field(default_factory=list)
    """视频"""

    vocal_beautifys: List = field(default_factory=list)
    """人声美化"""

    vocal_separations: List[VocalSeparation] = field(default_factory=list)
    """人声分离"""


class Config(BaseModel):
    adjust_max_index: int = 1
    """调整最大索引"""

    attachment_info: List = field(default_factory=list)
    """附件信息"""

    combination_max_index: int = 1
    """组合最大索引"""

    export_range: Any = None
    """导出范围"""

    extract_audio_last_index: int = 1
    """提取音频最后索引"""

    lyrics_recognition_id: str = ""
    """歌词识别ID"""

    lyrics_sync: bool = True
    """歌词同步"""

    lyrics_taskinfo: List = field(default_factory=list)
    """歌词任务信息"""

    maintrack_adsorb: bool = True
    """主轨吸附"""

    material_save_mode: int = 0
    """材料保存模式"""

    multi_language_current: str = "none"
    """当前多语言"""

    multi_language_list: List = field(default_factory=list)
    """多语言列表"""

    multi_language_main: str = "none"
    """主多语言"""

    multi_language_mode: str = "none"
    """多语言模式"""

    original_sound_last_index: int = 1
    """原始声音最后索引"""

    record_audio_last_index: int = 1
    """录音最后索引"""

    sticker_max_index: int = 1
    """贴纸最大索引"""

    subtitle_keywords_config: Any = None
    """字幕关键词配置"""

    subtitle_recognition_id: str = ""
    """字幕识别ID"""

    subtitle_sync: bool = True
    """字幕同步"""

    subtitle_taskinfo: List = field(default_factory=list)
    """字幕任务信息"""

    system_font_list: List = field(default_factory=list)
    """系统字体列表"""

    video_mute: bool = False
    """视频静音"""

    zoom_info_params: Any = None
    """缩放信息参数"""


class DraftContent(BaseModel):
    # canvas_config: CanvasConfig = field(default_factory=lambda: CanvasConfig(
    #     height=1080,
    #     ratio="original",
    #     width=1920
    # ))
    canvas_config: Optional[CanvasConfig] = None
    """画布配置"""

    color_space: Optional[int] = None
    """色彩空间"""

    config: Optional[Config] = None
    """配置"""

    cover: Optional[str] = None
    """封面"""

    create_time: Optional[int] = None
    """创建时间"""

    duration: Optional[int] = None
    """持续时间(微秒)"""

    extra_info: Optional[Any] = None
    """额外信息"""

    fps: Optional[float] = None
    """FPS"""

    free_render_index_mode_on: Optional[bool] = None
    """自由渲染索引模式开启"""

    group_container: Optional[Any] = None
    """组容器"""

    # id: str = field(
    #     default_factory=lambda: UUID.random(upper=True, formats=[(8, '-'), (12, '-'), (16, '-'), (20, '-')]))
    # """ID"""
    id: Optional[str] = None

    keyframe_graph_list: Optional[List] = None
    """关键帧图表列表"""

    keyframes: Optional[Keyframes] = None
    """关键帧"""

    last_modified_platform: Optional[Platform] = None
    """最后修改平台"""

    materials: Materials = field(default_factory=Materials)
    """素材"""

    mutable_config: Optional[Any] = None
    """可变配置"""

    name: Optional[str] = None
    """名称"""

    new_version: Optional[str] = None
    """新版本"""

    platform: Optional[Platform] = None
    """平台"""

    relationships: Optional[List] = None
    """关系"""

    render_index_track_mode_on: Optional[bool] = None
    """渲染索引轨道模式开启"""

    retouch_cover: Optional[Any] = None
    """修饰封面"""

    source: Optional[str] = None
    """来源"""

    static_cover_image_path: Optional[str] = None
    """静态封面图片路径"""

    time_marks: Optional[Any] = None
    """时间标记"""

    tracks: List[Track] = field(default_factory=lambda: [Track(
        type="video",
    )])
    """轨道"""

    update_time: Optional[int] = None
    """更新时间"""

    version: Optional[int] = None
    """版本"""


# endregion


# region 剪映草稿
class JianYingDraft:

    def __init__(self, name: str, meta: DraftMetaInfo = None, content: DraftContent = None,
                 draft_root_path: str = None):
        """
        新建剪映草稿

        Args:
            name: 草稿名称
            meta: 草稿元信息
            content: 草稿内容
            draft_root_path: 草稿根目录
        """
        self.name = name
        """草稿名称"""
        self.draft_root_path = Path(draft_root_path)
        self.meta = meta or DraftMetaInfo()
        self.meta.draft_name = name
        self.meta.draft_root_path = str(self.draft_root_path)
        """草稿元信息"""
        self.meta_json_file: JsonFile | None = None
        """草稿元信息JSON文件"""
        self.content = content or DraftContent()
        # self.content.id = self.meta.draft_id
        """草稿内容"""
        self.content_json_file: JsonFile | None = None
        """草稿内容JSON文件"""
        self.git_repo = None
        """Git仓库"""

    # region 删除草稿
    def delete(self):
        """
        删除草稿
        """
        shutil.rmtree(str(self.draft_root_path / self.name))

    # endregion

    # region 保存草稿
    def save(self, git_message: str = None):
        """
        保存草稿到指定目录

        Args:
            git_message: 提交消息,如果指定了git_message,则会将草稿目录初始化为git仓库并提交,如果已经是git仓库,则只提交
        """
        directory = Directory(str(self.draft_root_path / self.name))
        self.meta_json_file: JsonFile = directory.new_file("draft_meta_info.json")
        self.meta.draft_fold_path = str(directory.path).replace("\\", "/")
        self.meta_json_file.write_pydanitc_model(self.meta)
        self.content_json_file: JsonFile = directory.new_file("draft_content.json")
        self.content_json_file.write_pydanitc_model(self.content)

        # directory.new_folders("common_attachment")
        # directory.new_folders("matting")
        # directory.new_folders("Resources\\audioAlg")
        # directory.new_folders("Resources\\videoAlg")
        # directory.new_folders("smart_crop")
        #
        # attachment_pc_common_json_file = JsonFile(str(directory.path / "attachment_pc_common.json"))
        # if not attachment_pc_common_json_file.exists():
        #     attachment_pc_common_json_file.write_content(
        #         """{"ai_packaging_infos":[],"ai_packaging_report_info":{"caption_id_list":[],"task_id":"","text_style":"","tos_id":"","video_category":""},"commercial_music_category_ids":[],"pc_feature_flag":0,"recognize_tasks":[],"template_item_infos":[],"unlock_template_ids":[]}""")
        #
        # draft_agency_config_json_file = JsonFile(str(directory.path / "draft_agency_config.json"))
        # if not draft_agency_config_json_file.exists():
        #     draft_agency_config_json_file.write_content(
        #         """{"marterials":null,"use_converter":false,"video_resolution":720}""")
        #
        # draft_biz_config_json_file = JsonFile(str(directory.path / "draft_biz_config.json"))
        # if not draft_biz_config_json_file.exists():
        #     draft_biz_config_json_file.write_content(""" """)
        if git_message:
            self.git_repo = GitRepository(str(directory.path), ignores=[
                # 忽略除了draft_meta_info.json和draft_content.json以外的所有文件
                "*",
                "!draft_meta_info.json",
                "!draft_content.json",
                "!attachment_pc_common.json",
                "!draft.extra",
                "!draft_agency_config.json",
                "!draft_biz_config.json",
                "draft_settings",
                "!.gitignore"
            ])
            self.git_repo.commit(git_message)

    # endregion

    # region 从本地加载草稿
    def reload(self):
        """
        重新加载草稿内容
        """
        self.content = self.content_json_file.read_dataclass_json_obj(DraftContent)

    # endregion

    # region 根据轨道类型获取所有片段
    def get_segments_by_track_type(self, type: str) -> List[Segment]:
        """
        根据轨道类型获取所有片段

        Args:
            type: 轨道类型

        Returns:
            List[Segment]: 片段列表
        """
        return [segment for track in self.content.tracks for segment in track.segments if track.type == type]

    # endregion

    # region 添加文本轨道
    def add_text_track(self, text: str, max_length_per_segment: int):
        """
        添加文本轨道

        在剪映客户端中添加一个文本轨道的逻辑是:

        1. 在tracks中添加一个 Track
        2. 如果有多个文本片段,则创建Segment然后添加到Track的segments中
        3. 为每个Segment在materials.texts中添加一个 TextMaterial
        4. 为每个Segment在materials.material_animations中添加一个 StickerAnimation
        5. 每个Segment的extra_material_refs中添加对应的StickerAnimation的id
        6. 每个Segment的material_id指向对应的TextMaterial的id

        Args:
            text: 文本内容
            max_length_per_segment: 每个片段的最大长度
        """
        font_size: float = 12.0
        scale: float = 1.0
        line_spacing: float = 0.02
        # 根据每个片段的最大长度获取轨道中每个片段的文本
        segment_texts = [text[i:i + max_length_per_segment] for i in range(0, len(text), max_length_per_segment)]
        text_track = Track(
            segments=[

            ],
            type="text"
        )
        for i, segment_text in enumerate(segment_texts):
            sticker_animation = StickerAnimation()
            text_content = TextContent(
                text=segment_text,
                styles=[
                    Style(
                        size=font_size,
                        range=[0, len(segment_text)]
                    )
                ]
            )
            text_material = TextMaterial(
                content=text_content.model_dump_json(
                    exclude_none=True,
                ),
                font_size=font_size,
                line_spacing=line_spacing,
            )
            segment = Segment(
                clip=Clip(
                    scale=Scale(
                        x=scale,
                        y=scale
                    )
                ),
                render_index=14003,
                extra_material_refs=[sticker_animation.id],
                material_id=text_material.id,
                target_timerange=TimeRange(
                    start=int(i * 3000000),
                    duration=3000000,
                ),
                hdr_settings=None,
                source_timerange=None,
                enable_adjust=False,
                enable_lut=False,
                # render_index=14001,
            )
            self.content.materials.material_animations.append(sticker_animation)
            self.content.materials.texts.append(text_material)
            text_track.segments.append(segment)
        # if self.content.color_space == -1:
        #     self.content.color_space = 0
        # 计算新的视频时长
        duration = 3000000 * len(segment_texts)
        if self.content.duration is None:
            self.content.duration = duration
        else:
            self.content.duration += duration
        # self.content.materials.material_animations按照id desc排序
        # self.content.materials.material_animations.sort(key=lambda x: x.id, reverse=True)
        # self.content.materials.texts.sort(key=lambda x: x.id, reverse=True)
        self.content.tracks.append(text_track)
    # endregion


def get_digit_human(self, index: int) -> DigitalHuman:
    """
    获取草稿中的数字人素材

    Args:
        index: 数字人索引

    Returns:
        DigitalHuman: 数字人
    """
    return self.content.materials.digital_humans[index]


# endregion


# region 剪映客户端
class JianYingDesktop:
    def __init__(self, executable_path: str, draft_root_path: str, locator_root_path: str,
                 render_digital_human_timeout: int = 60):
        """
        剪映桌面版

        Args:
            executable_path: 剪映桌面版可执行文件路径
            draft_root_path: 草稿根目录
            locator_root_path: 定位器根目录
            render_digital_human_timeout: 渲染数字人超时时间
        """
        self.executable_path = executable_path
        """剪映桌面版可执行文件路径"""
        self.locator_root_path = Path(locator_root_path)
        """定位器根目录"""
        self.cnstore_file = JsonFile(str(self.locator_root_path / "jianyingpro.cnstore"))
        """cnstore文件"""
        self.draft_root_path = Path(draft_root_path)
        """草稿根目录"""
        self.render_digital_human_timeout = render_digital_human_timeout
        """渲染数字人超时时间"""

        self.draft: JianYingDraft | None = None
        """客户端当前打开的草稿"""

    # region 图文成片
    def create_image_text_video(self, text):
        window = cc.find_element(locator=locator.jianyingpro.剪映主窗口)
        window.set_focus()
        ui(locator.jianyingpro.图文成片).click()
        ui(locator.jianyingpro.图片成片_自由编辑文案).click()
        sciprt_input = cc.find_element(locator=locator.jianyingpro.图文成片_自由编辑文案_文案输入框)
        pyperclip.copy(text)
        sciprt_input.send_hotkey('^v')
        # "生成视频"按钮定位不到,先定位到旁边的"选择声色"按钮,然后再向右移动
        ui(locator.jianyingpro.图文成片_选择声音).hover()
        pyautogui.moveRel(100, 0)
        pyautogui.click()

        @retry(stop=stop_after_delay(5), wait=wait_fixed(1))
        def wait_options_window():
            if not cc.is_existing(locator.jianyingpro.图文成片_点击生成视频按钮后出现的窗口):
                raise Exception("图文成片_点击生成视频按钮后出现的窗口未打开")
            return True

        if wait_options_window():
            image_location = pyautogui.locateOnScreen(
                rf'{str(self.locator_root_path)}/pyautogui/jianyingpro_img/use_local_material.png',
                confidence=0.8)
            image_center_point = pyautogui.center(image_location)
            center_point_x, center_point_y = image_center_point
            pyautogui.click(center_point_x, center_point_y)

    # endregion

    # region 打开剪映桌面版
    def start_process(self):
        """
        启动剪映桌面版

        Returns:
            bool: 如果成功启动剪映桌面版, 则返回True
        """
        # 已经启动则返回
        if ProcessManager.is_process_running("JianyingPro.exe"):
            started = True
        else:
            # 否则启动剪映桌面版,然后在15秒内每隔2秒检查是否启动成功
            subprocess.Popen(self.executable_path)

            @retry(stop=stop_after_delay(15), wait=wait_fixed(2))
            def is_started():
                if not ProcessManager.is_process_running("JianyingPro.exe"):
                    raise Exception("剪映桌面版启动失败")
                return True

            started = is_started()
        # 如果启动成功且弹出了草稿列表异常提示窗口,则点击取消按钮
        if started and cc.is_existing(locator.jianyingpro.草稿列表异常提示窗口):
            ui(locator.jianyingpro.草稿列表异常窗口上的取消按钮).click()
        return started

    # endregion

    # region 点击"开始创作"按钮,进入剪辑窗口
    def start_creation(self):
        """
        开始创作

        :return: 如果成功打开剪辑窗口, 则返回True, 否则返回False
        """
        ui(locator.jianyingpro.开始创作).click()

        @retry(stop=stop_after_attempt(5), wait=wait_fixed(2))
        def wait_main_window():
            if not cc.is_existing(locator.jianyingpro.剪辑窗口):
                raise Exception("剪辑窗口未打开")
            return True

        return wait_main_window()

    # endregion

    # region 打开草稿
    def open_draft(self, draft: JianYingDraft):
        """
        打开草稿

        Args:
            draft: 草稿对象

        Raises:
            Exception: 如果草稿未找到

        Returns:
            bool: 如果成功打开草稿, 则返回True
        """
        if not cc.is_existing(locator.jianyingpro.剪映主窗口):
            raise Exception("剪映主窗口未打开")

        @retry(stop=stop_after_attempt(5), wait=wait_fixed(1))
        def wait_draft_search_result():
            if not cc.is_existing(locator.jianyingpro.草稿列表中的第一个元素):
                raise Exception(f"未找到草稿: {draft.name}")
            return True

        # 如果搜索框不可见,则先点击搜索按钮
        if not cc.is_existing(locator.jianyingpro.草稿搜索框):
            ui(locator.jianyingpro.草稿搜索按钮).click()
        # 输入草稿名称
        ui(locator.jianyingpro.草稿搜索框).set_text(draft.name)
        # 等待搜索结果然后点击第一个结果
        if wait_draft_search_result():
            ui(locator.jianyingpro.草稿列表中的第一个元素).click()
        self.draft = draft

    # endregion

    # region 选择文本片段
    def select_text_segment(self, index_range: IntRange):
        """
        选择指定索引范围上的文本片段

        Args:
            index_range: 文本片段索引范围
        """
        # 先按下ctrl键
        #pyautogui.keyDown("ctrl")
        for index in index_range:
            params = {"index": index}
            # logger.info(f"选择文本片段: {index}")
            # self.cnstore_file.set_value_by_jsonpath(
            #     "locators[6].content.childControls[0].childControls[0].childControls[0].identifier.index.value",
            #     str(index))
            # self.cnstore_file.set_value_by_jsonpath(
            #     "locators[6].content.childControls[0].childControls[0].childControls[0].identifier.index.excluded",
            #     None)
            text_segment = ui(locator.jianyingpro.文本片段,params)
            if index == index_range.start:#如果是第一个文本片段，需要先hover一下，然后按下ctrl键
                text_segment.hover()
                pyautogui.keyDown("ctrl")
            text_segment.click()
        # 释放ctrl键
        pyautogui.keyUp("ctrl")
        # time.sleep(3)
        # ui(locator.jianyingpro.文本轨道1)
    # endregion

    # region 添加数字人
    def add_digital_human(self, index_range: IntRange, digital_human_index: int):
        """
        添加数字人

        Args:
            index_range:   文本片段索引范围
            digital_human_index: 数字人索引


        Returns:
            如果数字人生成成功, 则返回数字人视频文件
        """
        self.select_text_segment(index_range)

        @retry(stop=stop_after_attempt(5), wait=wait_fixed(1))
        def wait_digital_human_tab():
            """在5秒内等待文本轨道选择后出现"添加数字人"tab标签"""
            return pyautogui.locateOnScreen(
                rf'{str(self.locator_root_path)}/pyautogui/jianyingpro_img/1.png',
                confidence=0.8)

        image_location = wait_digital_human_tab()
        # 移动鼠标到"添加数字人"tab标签的中心位置
        image_center_point = pyautogui.center(image_location)
        center_point_x, center_point_y = image_center_point
        pyautogui.click(center_point_x, center_point_y)

        @retry(stop=stop_after_attempt(5), wait=wait_fixed(1))
        def wait_digital_human_list():
            if not cc.is_existing(locator.jianyingpro.数字人):
                raise Exception(f"加载数字人列表失败")
            return True

        if wait_digital_human_list():
            self.cnstore_file.set_value_by_jsonpath(
                "locators[7].content.childControls[0].childControls[0].identifier.index.value",
                str(digital_human_index))
            ui(locator.jianyingpro.数字人).click()

            @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
            def wait_add_digital_human_button():
                """在3秒内等待数字人列表加载完成后出现"添加数字人"按钮"""
                return pyautogui.locateOnScreen(
                    rf'{str(self.locator_root_path)}/pyautogui/jianyingpro_img/generate.png',
                    confidence=0.8)

            image_location = wait_add_digital_human_button()
            # 移动鼠标到"添加数字人"按钮的中心位置
            image_center_point = pyautogui.center(image_location)
            center_point_x, center_point_y = image_center_point
            time.sleep(1)
            pyautogui.click(center_point_x, center_point_y)
            print(f"在{center_point_x},{center_point_y}上点击了添加数字人按钮")

            # 现在去草稿下面的数字人目录等mp4文件出来
            # 可能会有多个文件,按创建时间和大小排序，然后取第一个
            # self.dr

            @retry(stop=stop_after_delay(self.render_digital_human_timeout), wait=wait_fixed(3))
            def wait_video_file():
                self.draft.reload()
                digital_human_local_task_id = self.draft.get_digit_human(0).local_task_id
                digital_human_video_dir = Directory(
                    str(self.draft_root_path / f"{self.draft.name}/Resources/digitalHuman"))
                digital_human_video_file = digital_human_video_dir.find_file(f"{digital_human_local_task_id}.mp4")
                if digital_human_video_file is None:
                    raise Exception(f"数字人视频文件未生成")
                return digital_human_video_file

            return wait_video_file()
    # endregion


# endregion


if __name__ == '__main__':
    # JianYingDraft.draft_root_path = Path(r"D:\ProgramData\JianyingPro Drafts")
    # draft = JianYingDraft(name="test")
    # draft.add_text_track("aaaaa")
    # draft.save("加了一个文本轨道")

    jianying = JianYingDesktop(r"D:\Program Files\JianyingPro5.9.0\JianyingPro.exe")
    # jianying.start_process()
    # print(jianying.start_creation())
    # jianying.open_draft("test")
    # jianying.select_text_track(3)
    jianying.add_digital_human(1, 6)
