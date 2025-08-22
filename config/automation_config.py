"""
Configuration for streak-based trading automation
"""

# ===== STREAK-BASED AUTOMATION SETTINGS =====

# Enable/disable the automation system
STREAK_AUTOMATION_ENABLED = True

# Number of consecutive positive days required to enable trading
REQUIRED_POSITIVE_DAYS = 5

# Minimum profit threshold for a day to be considered "positive"
# Set to 0.0 to consider any profit as positive, or higher for stricter criteria
MIN_PROFIT_THRESHOLD = 0.0

# How often to check streak conditions (in seconds)
# Default: 24 hours
AUTOMATION_CHECK_INTERVAL = 24 * 60 * 60

# ===== ADVANCED SETTINGS =====

# Maximum number of days to keep in streak history
MAX_STREAK_HISTORY_DAYS = 30

# Whether to log detailed streak information
VERBOSE_STREAK_LOGGING = True

# Emergency override - force trading to be enabled regardless of streaks
EMERGENCY_OVERRIDE = True

# ===== NOTIFICATION SETTINGS =====

# Whether to send notifications when trading is enabled/disabled
ENABLE_NOTIFICATIONS = False

# Notification settings (for future implementation)
NOTIFICATION_CHANNELS = {
    'email': False,
    'slack': False,
    'discord': False
} 