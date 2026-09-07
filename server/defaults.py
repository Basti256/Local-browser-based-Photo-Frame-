"""Standardwerte der Projektkonfiguration und Schlüssel-Migration."""

DEFAULT_CONFIG = {
    "wall_view_mode": "fly",
    "grid_columns": 4,
    "grid_animation_duration": 8,
    "grid_show_frames": True,
    "grid_spacing_rows": 0,
    "grid_spacing_columns": 20,
    "network_mode": "network",
    "public_host": "",
    "public_https": False,
    "public_base_url": "",
    "storage_mode": "project",
    "storage_path": "",
    "port": 8000,
    "image_spawn_interval": 6,
    "spawn_mode": "lanes",
    "spawn_lane_count": 6,
    "spawn_lane_order": "random_apart",
    "spawn_burst_period": 1.0,
    "max_images_on_screen": 10,
    "image_min_size": 100,
    "image_max_size": 150,
    "max_videos_on_screen": 2,
    "video_playback_mode": "once",
    "video_spawn_interval": 10,
    "video_min_size": 100,
    "video_max_size": 150,
    "image_rotation_strength": 90,
    "image_drift_strength": 0.2,
    "image_rotation_direction_mode": "both",
    "image_flight_path_mode": "random",
    "image_animation_duration": 30,
    "image_speed_variation_enabled": True,
    "image_speed_variation_strength": 0.4,
    "image_highlight_new": True,
    "image_highlight_duration": 10,
    "image_highlight_color": "#ffff00",
    "image_max_simultaneous_highlights": 3,
    "video_rotation_strength": 90,
    "video_drift_strength": 0.2,
    "video_rotation_direction_mode": "both",
    "video_flight_path_mode": "random",
    "video_animation_duration": 30,
    "video_speed_variation_enabled": True,
    "video_speed_variation_strength": 0.4,
    "video_highlight_new": True,
    "video_highlight_duration": 10,
    "video_highlight_color": "#ffff00",
    "video_max_simultaneous_highlights": 3,
    "center_highlight_enabled": False,
    "center_highlight_duration": 5,
    "center_highlight_mode": "fly",
    "center_highlight_entry_speed": 1.0,
    "center_highlight_exit_speed": 1.0,
    "center_highlight_screen_percent": 30,
    "center_highlight_max_simultaneous": 1,
    "center_highlight_position_variation": 30,
    "show_qr_code": True,
    "qr_text": "Schick uns dein Bild!",
    "qr_size": 220,
    "qr_text_size": 24,
    "qr_position": "center-bottom",
    "qr_text_color": "#db0a0a",
    "qr_dynamic_enabled": True,
    "qr_show_duration": 5,
    "qr_hide_duration": 5,
    "banner_enabled": False,
    "banner_text": "",
    "banner_position": "bottom",
    "banner_height": 120,
    "banner_color": "#000000",
    "banner_text_color": "#ffffff",
    "banner_show_duration": 10,
    "banner_hide_duration": 10,
    "banner_align": "center",
    "banner_font": "Arial",
    "cache_enabled": False,
    "cache_ttl_minutes": 30,
    "cache_max_images": 100,
    "cache_max_videos": 20,
    "cache_max_size_mb": 500,
    "debug_overlay": False,
    "debug_random_comments": False,
    "screen_wake_lock_enabled": False,
    "screen_wake_lock_alternative": False,
    "upload_greeting": "Lade deine Fotos hoch",
    "upload_greeting_align": "center",
    "upload_greeting_font": "Arial",
    "upload_greeting_color": "#222222",
    "upload_greeting_size": 28,
    "upload_greeting_bold": True,
    "upload_greeting_underline": False,
    "upload_image": "",
    "upload_image_rotation": 0,
    "upload_button_color": "#ff4b5c",
    "upload_allow_videos": True,
    "upload_max_files": 20,
    "upload_max_file_size_mb": 50,
    "frame_padding_top": 12,
    "frame_padding_side": 12,
    "frame_padding_bottom": 50,
    "comments_enabled": True,
    "comment_font": "Pacifico",
    "comment_color": "#e51515",
    "comment_size": 22,
    "comment_bold": False,
    "comment_underline": False,
    "comment_max_length": 80,
    "background_mode": "color",
    "background_color": "#000000",
    "background_image": "",
    "background_rotation": 0,
    "background_brightness": 100,
    "background_contrast": 100,
    "background_position": "center",
    "background_scale": 100,
    "background_opacity": 100,
    "transcode_enabled": True,
    "transcode_image_max_edge": 1920,
    "transcode_image_quality": 85,
    "transcode_keep_original": True,
}

NETWORK_MODES = ("network", "public")
STORAGE_MODES = ("project", "folder")
TEXT_ALIGNS = ("left", "center", "right")
SPAWN_LANE_ORDERS = ("random", "random_apart", "adjacent")
SPAWN_MODES = ("lanes", "burst", "random")
NETWORK_MODE_ALIASES = {
    "internal": "network",
    "local": "network",
    "tunnel": "public",
}

CONFIG_MIGRATION = [
    ("rotation_strength", "image_rotation_strength", "video_rotation_strength"),
    ("drift_strength", "image_drift_strength", "video_drift_strength"),
    ("rotation_direction_mode", "image_rotation_direction_mode", "video_rotation_direction_mode"),
    ("flight_path_mode", "image_flight_path_mode", "video_flight_path_mode"),
    ("animation_duration", "image_animation_duration", "video_animation_duration"),
    ("speed_variation_enabled", "image_speed_variation_enabled", "video_speed_variation_enabled"),
    ("speed_variation_strength", "image_speed_variation_strength", "video_speed_variation_strength"),
    ("highlight_new_images", "image_highlight_new", "video_highlight_new"),
    ("highlight_duration", "image_highlight_duration", "video_highlight_duration"),
    ("highlight_color", "image_highlight_color", "video_highlight_color"),
    ("max_simultaneous_highlights", "image_max_simultaneous_highlights", "video_max_simultaneous_highlights"),
]


def migrate_config(config: dict) -> tuple[dict, bool]:
    changed = False
    mode = config.get("network_mode")
    if mode in NETWORK_MODE_ALIASES:
        config["network_mode"] = NETWORK_MODE_ALIASES[mode]
        changed = True
    if config.get("network_mode") not in NETWORK_MODES:
        config["network_mode"] = "network"
        changed = True
    if not config.get("public_host") and config.get("public_base_url"):
        host = str(config.get("public_base_url") or "")
        lowered = host.lower()
        if lowered.startswith("https://"):
            config["public_https"] = True
            changed = True
            host = host[8:]
        elif lowered.startswith("http://"):
            host = host[7:]
        config["public_host"] = host.split("/")[0]
        changed = True

    for old_key, img_key, vid_key in CONFIG_MIGRATION:
        if old_key in config:
            if img_key not in config:
                config[img_key] = config[old_key]
                changed = True
            if vid_key not in config:
                config[vid_key] = config[old_key]
                changed = True

    if "grid_animation_duration" not in config and "grid_interval" in config:
        config["grid_animation_duration"] = config["grid_interval"]
        changed = True

    if "grid_spacing_columns" not in config and "grid_spacing_rows" in config:
        config["grid_spacing_columns"] = config["grid_spacing_rows"]
        changed = True
    if "grid_spacing" in config:
        config["grid_spacing_rows"] = config["grid_spacing"]
        changed = True

    if "center_highlight_screen_percent" not in config and "center_highlight_scale" in config:
        scale = float(config.get("center_highlight_scale", 1.6))
        config["center_highlight_screen_percent"] = min(100, max(5, int(scale * 15)))
        changed = True

    if "video_min_size" not in config and "image_min_size" in config:
        config["video_min_size"] = config["image_min_size"]
        changed = True
    if "video_max_size" not in config and "image_max_size" in config:
        config["video_max_size"] = config["image_max_size"]
        changed = True

    for key, value in DEFAULT_CONFIG.items():
        if key not in config:
            config[key] = value
            changed = True

    if config.get("background_position") not in ("center", "top", "bottom"):
        config["background_position"] = "center"
        changed = True
    try:
        lanes = int(config.get("spawn_lane_count", DEFAULT_CONFIG["spawn_lane_count"]))
    except (TypeError, ValueError):
        lanes = DEFAULT_CONFIG["spawn_lane_count"]
    lanes = max(1, min(20, lanes))
    if config.get("spawn_lane_count") != lanes:
        config["spawn_lane_count"] = lanes
        changed = True
    order = str(config.get("spawn_lane_order") or DEFAULT_CONFIG["spawn_lane_order"]).strip().lower()
    if order not in SPAWN_LANE_ORDERS:
        order = DEFAULT_CONFIG["spawn_lane_order"]
    if config.get("spawn_lane_order") != order:
        config["spawn_lane_order"] = order
        changed = True
    mode = str(config.get("spawn_mode") or DEFAULT_CONFIG["spawn_mode"]).strip().lower()
    if mode not in SPAWN_MODES:
        mode = DEFAULT_CONFIG["spawn_mode"]
    if config.get("spawn_mode") != mode:
        config["spawn_mode"] = mode
        changed = True
    try:
        burst = float(config.get("spawn_burst_period", DEFAULT_CONFIG["spawn_burst_period"]))
    except (TypeError, ValueError):
        burst = DEFAULT_CONFIG["spawn_burst_period"]
    burst = max(0.1, round(burst * 10) / 10)
    if config.get("spawn_burst_period") != burst:
        config["spawn_burst_period"] = burst
        changed = True

    for align_key in ("banner_align", "upload_greeting_align"):
        align = str(config.get(align_key) or "center").strip().lower()
        if align not in TEXT_ALIGNS:
            align = "center"
        if config.get(align_key) != align:
            config[align_key] = align
            changed = True
    try:
        rot = int(config.get("background_rotation") or 0)
    except (TypeError, ValueError):
        rot = 0
    rot = ((rot // 90) * 90) % 360
    if rot not in (0, 90, 180, 270):
        rot = 0
    if config.get("background_rotation") != rot:
        config["background_rotation"] = rot
        changed = True
    try:
        hrot = int(config.get("upload_image_rotation") or 0)
    except (TypeError, ValueError):
        hrot = 0
    hrot = ((hrot // 90) * 90) % 360
    if hrot not in (0, 90, 180, 270):
        hrot = 0
    if config.get("upload_image_rotation") != hrot:
        config["upload_image_rotation"] = hrot
        changed = True
    for key, lo, hi in (
        ("background_brightness", 20, 180),
        ("background_contrast", 20, 180),
        ("background_scale", 20, 300),
        ("background_opacity", 0, 100),
    ):
        try:
            n = int(config.get(key, DEFAULT_CONFIG[key]))
        except (TypeError, ValueError):
            n = DEFAULT_CONFIG[key]
        n = max(lo, min(hi, n))
        if config.get(key) != n:
            config[key] = n
            changed = True

    try:
        cmax = int(config.get("comment_max_length", DEFAULT_CONFIG["comment_max_length"]))
    except (TypeError, ValueError):
        cmax = DEFAULT_CONFIG["comment_max_length"]
    cmax = max(1, min(500, cmax))
    if config.get("comment_max_length") != cmax:
        config["comment_max_length"] = cmax
        changed = True

    return config, changed
