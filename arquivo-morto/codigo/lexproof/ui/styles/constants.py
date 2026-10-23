"""Shared design constants for the LexProof UI.

All values use system font and palette-derived colors.
No hardcoded hex colors — everything goes through QPalette.
"""

from __future__ import annotations

# --- Spacing (8px grid) ---
SPACING_XS = 4
SPACING_SM = 8
SPACING_MD = 12
SPACING_LG = 16
SPACING_XL = 24
SPACING_XXL = 32
SPACING_XXXL = 40

# --- Border Radius ---
RADIUS_SM = 4
RADIUS_MD = 6
RADIUS_LG = 8
RADIUS_XL = 10
RADIUS_XXL = 12

# --- Sidebar ---
SIDEBAR_COLLAPSED_WIDTH = 64
SIDEBAR_EXPANDED_WIDTH = 220
SIDEBAR_ICON_SIZE = 22
SIDEBAR_ITEM_HEIGHT = 40
SIDEBAR_ITEM_RADIUS = 8

# --- Cards ---
CARD_RADIUS = 10
CARD_PADDING = 16
CARD_MIN_WIDTH = 200
CARD_MIN_HEIGHT = 100
CARD_SHADOW_BLUR = 24
CARD_SHADOW_Y = 4

# --- Toast ---
TOAST_WIDTH = 360
TOAST_HEIGHT = 56
TOAST_RADIUS = 8
TOAST_PADDING = 12

# --- Status Bar ---
STATUSBAR_HEIGHT = 28

# --- Welcome Tab ---
WELCOME_MAX_WIDTH = 900
WELCOME_DROP_MIN_HEIGHT = 180

# --- Wizard ---
WIZARD_MIN_WIDTH = 720
WIZARD_MIN_HEIGHT = 520
WIZARD_CIRCLE_SIZE = 36

# --- Step Indicator ---
STEP_CIRCLE_SIZE = 32
STEP_CONNECTOR_MIN_WIDTH = 40
