import shutil
import subprocess
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Union, Any, Optional

import pyautogui
from clicknium import clicknium as cc, ui, locator
from dataclasses_json import dataclass_json, config
from tenacity import retry, stop_after_attempt, stop_after_delay, wait_fixed

from pyext.commons import UUID, ProcessManager
from pyext.io import JsonFile, Directory, GitRepository


@dataclass
class TimeRange:
    """
    表示一个时间范围
    """

    duration: int = 0
    """持续时间"""

    start: int = 0
    """开始时间"""


@dataclass
class ImageMaterial:
    """
    图片素材
    """

    create_time: int
    """创建时间,Unix时间戳"""
    duration: int
    """持续时间,以微秒为单位"""

    extra_info: str
    """额外信息,例如文件名"""

    file_Path: str
    """文件路径"""

    height: int
    """图片高度,以像素为单位"""

    id: str
    """图片素材的唯一标识符"""

    import_time: int
    """导入时间,Unix时间戳"""

    import_time_ms: int
    """导入时间,以微秒为单位"""

    item_source: int
    """素材来源"""

    md5: str
    """文件的MD5哈希值,用于校验"""

    metetype: str
    """素材类型,例如 "photo" """

    roughcut_time_range: "TimeRange"
    """粗剪时间范围"""

    sub_time_range: "TimeRange"
    """子时间范围"""

    type: int
    """类型,例如`0`代表图片素材"""

    width: int
    """图片宽度,以像素为单位"""


@dataclass
class DraftMaterial:
    """
    表示草稿中的一个素材
    """

    type: int
    """素材类型"""

    value: List[Union[ImageMaterial]] = field(default_factory=list)
    """素材列表"""


@dataclass
class DraftEnterpriseInfo:
    """
    企业信息
    """

    draft_enterprise_extra: str = ""
    """企业额外信息"""

    draft_enterprise_id: str = ""
    """企业ID"""

    draft_enterprise_name: str = ""
    """企业名称"""

    enterprise_material: List = field(default_factory=list)
    """企业材料"""


@dataclass_json
@dataclass
class DraftMetaInfo:
    """
    草稿元信息
    """

    cloud_package_completed_time: str = ""
    """云端包完成时间"""

    draft_cloud_capcut_purchase_info: str = ""
    """云端Capcut购买信息"""

    draft_cloud_last_action_download: bool = False
    """云端最后动作是否为下载"""

    draft_cloud_materials: List = field(default_factory=list)
    """云端材料"""

    draft_cloud_purchase_info: str = ""
    """云端购买信息"""

    draft_cloud_template_id: str = ""
    """云端模板ID"""

    draft_cloud_tutorial_info: str = ""
    """云端教程信息"""

    draft_cloud_videocut_purchase_info: str = ""
    """云端视频剪辑购买信息"""

    draft_cover: str = "draft_cover.jpg"
    """草稿封面"""

    draft_deeplink_url: str = ""
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


@dataclass
class Type0Value:
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


@dataclass
class Type1Value:
    child_id: str
    """子ID"""

    parent_id: str
    """父ID"""


@dataclass
class DraftVirtualStoreItem:
    """
    草稿虚拟存储中的一个条目
    """

    type: int
    """类型"""

    value: List[Union[Type0Value, Type1Value]]
    """值"""


@dataclass_json
@dataclass
class DraftVirtualStore:
    draft_materials: List[DraftMaterial] = field(default_factory=list)
    """草稿材料"""

    draft_virtual_store: List[DraftVirtualStoreItem] = field(default_factory=list)
    """虚拟存储"""


# region draft_content.json
@dataclass
class CanvasConfig:
    height: int
    """画布高度"""

    ratio: str
    """画布比例"""

    width: int
    """画布宽度"""


@dataclass
class Platform:
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


@dataclass
class Keyframes:
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


@dataclass_json
@dataclass
class Canvas:
    album_image: str = ""
    """专辑图像"""

    blur: float = 0.0
    """模糊度"""

    color: str = ""
    """颜色"""

    id: str = uuid.uuid4().hex
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


@dataclass_json
@dataclass
class AudioConfig:
    audio_channel_mapping: int = 0
    """音频通道映射"""

    id: str = uuid.uuid4().hex
    """ID"""

    is_config_open: bool = False
    """配置是否开启"""

    type: str = "none"
    """类型"""


@dataclass_json
@dataclass
class SpeedConfig:
    curve_speed: Optional[float] = None
    """曲线速度"""

    id: str = uuid.uuid4().hex
    """ID"""

    mode: int = 0
    """模式"""

    speed: float = 1.0
    """速度"""

    type: str = "speed"
    """类型"""


@dataclass_json
@dataclass
class Crop:
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


@dataclass_json
@dataclass
class Matting:
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


@dataclass
class Stable:
    matrix_path: str = ""
    """矩阵路径"""

    stable_level: int = 0
    """稳定等级"""

    time_range: TimeRange = field(default_factory=TimeRange)
    """时间范围"""


@dataclass_json
@dataclass
class VideoAlgorithm:
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


@dataclass
class Photo:
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

    id: str = uuid.uuid4().hex
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


@dataclass_json
@dataclass
class VocalSeparation:
    choice: int = 0
    """选择"""

    id: str = uuid.uuid4().hex
    """ID"""

    production_path: str = ""
    """制作路径"""

    time_range: Optional[TimeRange] = None
    """时间范围"""

    type: str = "vocal_separation"
    """类型"""


@dataclass_json
@dataclass
class Flip:
    horizontal: bool = False
    """水平翻转"""

    vertical: bool = False
    """垂直翻转"""


@dataclass
class Scale:
    x: float = 1.0
    """x轴缩放"""

    y: float = 1.0
    """y轴缩放"""


@dataclass
class Transform:
    x: float = 0.0
    """x轴变换"""

    y: float = 0.0
    """y轴变换"""


@dataclass
class Clip:
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


@dataclass_json
@dataclass
class HDRSettings:
    intensity: float = 1.0
    """强度"""

    mode: int = 1
    """模式"""

    nits: int = 1000
    """尼特"""


@dataclass_json
@dataclass
class ResponsiveLayout:
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


@dataclass_json
@dataclass
class UniformScale:
    on: bool = True
    """启用"""

    value: float = 1.0
    """值"""


@dataclass
class Segment:
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

    id: str = uuid.uuid4().hex
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


@dataclass
class Track:
    attribute: int = 0
    """属性"""

    flag: int = 0
    """标志"""

    id: str = UUID.random(upper=True, formats=[(8, '-'), (12, '-'), (16, '-'), (20, '-')])
    """ID"""

    is_default_name: bool = True
    """是否默认名称"""

    name: str = ""
    """名称"""

    segments: List[Segment] = field(default_factory=list)
    """片段"""

    type: str = "video"
    """类型"""


@dataclass
class StickerAnimation:
    animations: List[str] = field(default_factory=list)
    """动画"""

    id: str = uuid.uuid4().hex
    """ID"""

    multi_language_current: str = "none"
    """多语言当前状态"""

    type: str = "sticker_animation"
    """类型"""


@dataclass
class CaptionTemplateInfo:
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


@dataclass_json
@dataclass
class ComboInfo:
    text_templates: List[str] = field(default_factory=list)
    """文本模板"""


@dataclass
class ShadowPoint:
    x: float = 0.6363961030678928
    """x轴阴影点"""

    y: float = -0.6363961030678928
    """y轴阴影点"""


@dataclass
class Words:
    end_time: List[str] = field(default_factory=list)
    """结束时间"""

    start_time: List[str] = field(default_factory=list)
    """开始时间"""

    text: List[str] = field(default_factory=list)
    """文本"""


@dataclass
class Solid:
    alpha: float = None
    """透明度"""

    color: List[float] = (1.0, 1.0, 1.0)
    """颜色"""


@dataclass
class Content:
    render_type: str = "solid"
    """渲染类型"""

    solid: Solid = field(default_factory=Solid)
    """实心"""


@dataclass
class Fill:
    alpha: float = field(default_factory=float, metadata=config(exclude=lambda x: x == 0.0))
    """透明度"""

    content: Content = field(default_factory=Content)
    """内容"""

    width: float = 0.0
    """宽度"""


@dataclass
class Font:
    id: str = ""
    """字体ID"""

    path: str = "D:/Program Files/JianyingPro5.9.0/5.9.0.11632/Resources/Font/SystemFont/zh-hans.ttf"
    """字体路径"""


@dataclass
class Style:
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

    useLetterColor: bool = False
    """使用字母颜色"""


@dataclass_json
@dataclass
class TextContent:
    styles: List[Style] = field(default_factory=list)
    """样式"""

    text: str = "默认文本"
    """文本"""


@dataclass
class Text:
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

    font_size: float = 15.0
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

    id: str = UUID.random(upper=True, formats=[(8, '-'), (12, '-'), (16, '-'), (20, '-')])
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


@dataclass
class Materials:
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

    digital_humans: List = field(default_factory=list)
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

    texts: List[Text] = field(default_factory=list)
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


@dataclass
class Config:
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


@dataclass_json
@dataclass
class DraftContent:
    canvas_config: CanvasConfig = field(default_factory=lambda: CanvasConfig(
        height=1080,
        ratio="original",
        width=1920
    ))
    """画布配置"""

    color_space: int = -1
    """色彩空间"""

    config: Config = field(default_factory=Config)
    """配置"""

    cover: Any = None
    """封面"""

    create_time: int = 0
    """创建时间"""

    duration: int = 3000000
    """持续时间(微秒)"""

    extra_info: Any = None
    """额外信息"""

    fps: float = 30.0
    """FPS"""

    free_render_index_mode_on: bool = False
    """自由渲染索引模式开启"""

    group_container: Any = None
    """组容器"""

    id: str = uuid.uuid4().hex
    """ID"""

    keyframe_graph_list: List = field(default_factory=list)
    """关键帧图表列表"""

    keyframes: Keyframes = field(default_factory=Keyframes)
    """关键帧"""

    last_modified_platform: Platform = field(default_factory=Platform)
    """最后修改平台"""

    materials: Materials = field(default_factory=Materials)
    """素材"""

    mutable_config: Any = None
    """可变配置"""

    name: str = ""
    """名称"""

    new_version: str = "110.0.0"
    """新版本"""

    platform: Platform = field(default_factory=Platform)
    """平台"""

    relationships: List = field(default_factory=list)
    """关系"""

    render_index_track_mode_on: bool = False
    """渲染索引轨道模式开启"""

    retouch_cover: Any = None
    """修饰封面"""

    source: str = "default"
    """来源"""

    static_cover_image_path: str = ""
    """静态封面图片路径"""

    time_marks: Any = None
    """时间标记"""

    tracks: List[Track] = field(default_factory=list)
    """轨道"""

    update_time: int = 0
    """更新时间"""

    version: int = 360000
    """版本"""


# endregion


# region 剪映草稿
class JianYingDraft:

    def __init__(self, name: str, meta: DraftMetaInfo = DraftMetaInfo(), content: DraftContent = DraftContent(),
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
        self.meta = meta
        self.meta.draft_name = name
        self.meta.draft_root_path = str(self.draft_root_path)
        """草稿元信息"""
        self.meta_json_file = None
        """草稿元信息JSON文件"""
        self.content = content
        self.content.id = self.meta.draft_id
        """草稿内容"""
        self.content_json_file = None
        """草稿内容JSON文件"""
        self.git_repo = None
        """Git仓库"""

    def delete(self):
        """
        删除草稿
        """
        shutil.rmtree(str(self.draft_root_path / self.name))

    def save(self, git_message: str = None):
        """
        保存草稿到指定目录

        :param git_message: 提交消息,如果指定了git_message,则会将草稿目录初始化为git仓库并提交,如果已经是git仓库,则只提交
        """
        directory = Directory(str(self.draft_root_path / self.name))
        self.meta_json_file: JsonFile = directory.new_file("draft_meta_info.json")
        self.meta.draft_fold_path = str(directory.path)
        self.meta_json_file.write_dataclass_json_obj(self.meta)
        self.content_json_file: JsonFile = directory.new_file("draft_content.json")
        self.content_json_file.write_dataclass_json_obj(self.content)
        if git_message:
            self.git_repo = GitRepository(str(directory.path))
            self.git_repo.commit(git_message)

    def add_text_track(self, text: str, font_size: float = 12.0, scale: float = 1.0, line_spacing: float = 0.02):
        """
        添加文本轨道

        Args:
            text: 文本内容
            font_size: 字体大小
            scale: 缩放比例
            line_spacing: 行间距
        """
        sticker_animation = StickerAnimation()
        text_content = TextContent(
            text=text,
            styles=[
                Style(
                    size=font_size,
                    range=[0, len(text)]
                )
            ]
        )
        text = Text(
            content=text_content.to_json(),
            font_size=font_size,
            line_spacing=line_spacing,
        )
        text_track = Track(
            segments=[
                Segment(
                    clip=Clip(
                        scale=Scale(
                            x=scale,
                            y=scale
                        )
                    ),
                    extra_material_refs=[sticker_animation.id],
                    material_id=text.id,
                    target_timerange=TimeRange(
                        duration=3000000,
                    ),
                    hdr_settings=None,
                    source_timerange=None,
                    enable_adjust=False,
                    enable_lut=False,
                    # render_index=14001,
                )
            ],
            type="text"
        )
        self.content.materials.material_animations.append(sticker_animation)
        self.content.materials.texts.append(text)
        self.content.tracks.append(text_track)


# endregion


# region 剪映客户端
class JianYingDesktop:
    def __init__(self, executable_path: str, draft_root_path: str, locator_root_path: str):
        """
        剪映桌面版

        Args:
            executable_path: 剪映桌面版可执行文件路径
            draft_root_path: 草稿根目录
            locator_root_path: 定位器根目录
        """
        self.executable_path = executable_path
        """剪映桌面版可执行文件路径"""
        self.locator_root_path = Path(locator_root_path)
        """定位器根目录"""
        self.cnstore_file = JsonFile(str(self.locator_root_path / "jianyingpro.cnstore"))
        """cnstore文件"""
        self.draft_root_path = Path(draft_root_path)
        """草稿根目录"""

    def start_process(self):
        """
        启动剪映桌面版

        Returns:
            bool: 如果成功启动剪映桌面版, 则返回True
        """
        subprocess.Popen(self.executable_path)

        @retry(stop=stop_after_delay(15), wait=wait_fixed(2))
        def is_started():
            if not ProcessManager.is_process_running("JianyingPro.exe"):
                raise Exception("剪映桌面版启动失败")
            return True

        return is_started()

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

    def open_draft(self, draft_name: str):
        """
        打开草稿

        Args:
            draft_name: 草稿名称

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
                raise Exception(f"未找到草稿: {draft_name}")
            return True

        # 如果搜索框不可见,则先点击搜索按钮
        if not cc.is_existing(locator.jianyingpro.草稿搜索框):
            ui(locator.jianyingpro.草稿搜索按钮).click()
        # 输入草稿名称
        ui(locator.jianyingpro.草稿搜索框).set_text(draft_name)
        # 等待搜索结果然后点击第一个结果
        if wait_draft_search_result():
            ui(locator.jianyingpro.草稿列表中的第一个元素).click()

    def select_text_track(self, track_index: int):
        """
        选择文本轨道

        Args:
            track_index: 文本轨道索引,从上往下数,从1开始
        """
        self.cnstore_file.set_value_by_jsonpath(
            "locators[6].content.childControls[0].childControls[0].childControls[0].identifier.index.value",
            str(track_index))
        self.cnstore_file.set_value_by_jsonpath(
            "locators[6].content.childControls[0].childControls[0].childControls[0].identifier.index.excluded",
            None)
        ui(locator.jianyingpro.文本轨道).click()
        # time.sleep(3)
        # ui(locator.jianyingpro.文本轨道1)

    def add_digital_human(self, text_track_index: int, digital_human_index: int):
        """
        添加数字人

        Args:
            text_track_index:   生成数字人需要一个文本轨道
            digital_human_index: 数字人索引
        """
        self.select_text_track(text_track_index)
        # 先找到"添加数字人"tab标签的位置
        image_location = pyautogui.locateOnScreen(
            rf'{str(self.locator_root_path)}/pyautogui/jianyingpro_img/1.png',
            confidence=0.8)
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
            image_location = pyautogui.locateOnScreen(
                r'..\.locator\pyautogui\jianyingpro_img\generate.png',
                confidence=0.8)
            # 移动鼠标到"添加数字人"tab标签的中心位置
            image_center_point = pyautogui.center(image_location)
            center_point_x, center_point_y = image_center_point
            pyautogui.click(center_point_x, center_point_y)
            # 现在去草稿下面的数字人目录等mp4文件出来
            # 可能会有多个文件,按创建时间和大小排序，然后取第一个


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
