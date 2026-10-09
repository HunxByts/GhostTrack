"""Curated active profile routes (reviewed October 2026).

Only GitHub and GitLab are verified via supported public user APIs. The rest
are profile URL templates, NOT evidence that an account exists.
Legacy/abandoned routes such as Ello, StumbleUpon and Periscope are excluded.
"""

PROFILES = (
    ("GitHub", "https://github.com/{username}"),
    ("GitLab", "https://gitlab.com/{username}"),
    ("Reddit", "https://www.reddit.com/user/{username}/"),
    ("Instagram", "https://www.instagram.com/{username}/"),
    ("X", "https://x.com/{username}"),
    ("TikTok", "https://www.tiktok.com/@{username}"),
    ("YouTube", "https://www.youtube.com/@{username}"),
    ("LinkedIn", "https://www.linkedin.com/in/{username}/"),
    ("Facebook", "https://www.facebook.com/{username}"),
    ("Pinterest", "https://www.pinterest.com/{username}/"),
    ("Twitch", "https://www.twitch.tv/{username}"),
    ("Telegram", "https://t.me/{username}"),
    ("Medium", "https://medium.com/@{username}"),
    ("SoundCloud", "https://soundcloud.com/{username}"),
    ("Behance", "https://www.behance.net/{username}"),
    ("Dribbble", "https://dribbble.com/{username}"),
)
