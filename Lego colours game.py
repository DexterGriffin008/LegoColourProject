import pygame
import pandas as pd
import random
import sys
import colorsys
from pathlib import Path

DATA_PATH = Path("EPQ sanatised colours.csv No modulex.txt")

WINDOW_W, WINDOW_H = 1200, 800
FPS = 60
NUM_CHOICES = 4

# Filters
EXCLUDE_NON_SYSTEM = True
FILTER_TRANSPARENCY = None         # None, "opaque", "trans"
YEAR_RANGE = (1950, 2025)

def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["y2"] = df["y2"].fillna(2025).astype(int)

    if EXCLUDE_NON_SYSTEM:
        lower = df["name"].str.lower()
        exclude_keywords = ["modulex", "duplo", "clikits", "fabuland", "ho "]
        mask = pd.Series(False, index=df.index)
        for kw in exclude_keywords:
            mask |= lower.str.contains(kw, na=False)
        df = df[~mask].copy()

    if FILTER_TRANSPARENCY == "opaque":
        df = df[df["is_trans"] == False].copy()
    elif FILTER_TRANSPARENCY == "trans":
        df = df[df["is_trans"] == True].copy()

    start, end = YEAR_RANGE
    df = df[(df["y1"] <= end) & (df["y2"] >= start)].copy()
    df = df.drop_duplicates(subset=["name"])

    def hex_to_hsv(hex_str):
        hex_str = str(hex_str).strip().lstrip("#")
        r = int(hex_str[0:2], 16) / 255.0
        g = int(hex_str[2:4], 16) / 255.0
        b = int(hex_str[4:6], 16) / 255.0
        h, s, v = colorsys.rgb_to_hsv(r, g, b)
        return h * 360, s, v

    df[["hue", "saturation", "value"]] = df["rgb"].apply(lambda x: pd.Series(hex_to_hsv(x)))
    return df.reset_index(drop=True)

def hex_to_rgb_tuple(hex_str):
    hex_str = str(hex_str).strip().lstrip("#")
    return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))

class QuizEngine:
    def __init__(self, df: pd.DataFrame, num_choices: int):
        if len(df) < num_choices:
            raise ValueError("Not enough colours to build a quiz after filtering.")
        self.df = df
        self.num_choices = num_choices
        self.score = 0
        self.rounds = 0
        self.streak = 0
        self.last_correct = None
        self.last_correct_name = None

    def new_question(self):
        correct_row = self.df.sample(1).iloc[0]
        correct_name = correct_row["name"]
        correct_rgb = correct_row["rgb"]
        correct_is_trans = bool(correct_row["is_trans"])

        pool = self.df[self.df["name"] != correct_name]
        if "is_trans" in pool.columns:
            pool = pool[pool["is_trans"] == correct_is_trans]

        need = self.num_choices - 1
        if len(pool) < need:
            pool = self.df[self.df["name"] != correct_name]
        distractors = pool.sample(need, replace=len(pool) < need)

        options = [correct_name] + distractors["name"].tolist()
        random.shuffle(options)
        return {"swatch_rgb": correct_rgb, "correct_name": correct_name, "options": options}

    def submit(self, chosen: str, correct: str):
        self.rounds += 1
        if chosen == correct:
            self.score += 1
            self.streak += 1
            self.last_correct = True
            self.last_correct_name = correct
            return True
        else:
            self.streak = 0
            self.last_correct = False
            self.last_correct_name = correct
            return False


pygame.init()
screen = pygame.display.set_mode((WINDOW_W, WINDOW_H), pygame.RESIZABLE)
pygame.display.set_caption("LEGO Colour Quiz")
clock = pygame.time.Clock()

def make_fonts(base_scale=1.0):
    # Adaptive font sizes based on window height
    h1 = max(28, int(48 * base_scale))
    h2 = max(20, int(32 * base_scale))
    m  = max(18, int(26 * base_scale))
    s  = max(14, int(20 * base_scale))
    return (pygame.font.SysFont("arial", h1),
            pygame.font.SysFont("arial", h2),
            pygame.font.SysFont("arial", m),
            pygame.font.SysFont("arial", s))

# Palette
BG        = (16, 16, 20)
CARD      = (30, 32, 38)
CARD_EDGE = (60, 64, 72)
TEXT      = (235, 238, 245)
TEXT_DIM  = (180, 190, 205)
OK        = (64, 190, 120)
BAD       = (230, 85, 95)
HOVER     = (40, 44, 52)
BTN       = (35, 38, 45)

def draw_text(surface, text, font, color, center=None, topleft=None):
    s = font.render(text, True, color)
    r = s.get_rect()
    if center: r.center = center
    if topleft: r.topleft = topleft
    surface.blit(s, r)
    return r

def rounded_rect(surface, rect, color, radius=12, width=0):
    pygame.draw.rect(surface, color, rect, width=width, border_radius=radius)


def compute_layout(w, h, num_choices, fonts):
    FONT_H1, FONT_H2, FONT_M, FONT_S = fonts
    margin = int(h * 0.04)

    header_y = margin + FONT_H1.get_height() // 2
    stats_y1 = header_y + FONT_H1.get_height() + margin // 2
    stats_y2 = stats_y1 + FONT_H2.get_height() + int(margin * 0.4)

    # Swatch card size based on height
    swatch_h = int(h * 0.33)
    swatch_w = int(min(w * 0.78, w - 2 * margin))
    swatch_x = (w - swatch_w) // 2
    swatch_y = stats_y2 + FONT_H2.get_height() + margin
    swatch_rect = pygame.Rect(swatch_x, swatch_y, swatch_w, swatch_h)

    # Buttons area
    available_h = h - (swatch_y + swatch_h) - margin - FONT_S.get_height() - margin
    # Start with comfortable sizes
    btn_w = int(min(w * 0.65, w - 2 * margin))
    btn_h = int(max(56, min(80, available_h // (num_choices + 1))))
    btn_gap = max(16, int((available_h - num_choices * btn_h) / max(1, num_choices)))
    btn_x = (w - btn_w) // 2
    btn_start_y = swatch_y + swatch_h + int(btn_gap * 0.6)

    # If still overflowing, shrink buttons further
    total_btn_h = num_choices * btn_h + (num_choices - 1) * btn_gap
    overflow = (btn_start_y + total_btn_h + margin + FONT_S.get_height()) - h
    if overflow > 0:
        # Reduce button height and gap proportionally
        reduce_each = overflow / num_choices
        btn_h = max(48, btn_h - int(reduce_each * 0.7))
        btn_gap = max(12, btn_gap - int(reduce_each * 0.3))
        total_btn_h = num_choices * btn_h + (num_choices - 1) * btn_gap
        btn_start_y = swatch_y + swatch_h + int(btn_gap * 0.6)

    btn_rects = [pygame.Rect(btn_x, btn_start_y + i * (btn_h + btn_gap), btn_w, btn_h)
                 for i in range(num_choices)]

    footer_y = h - margin
    return {
        "header_y": header_y,
        "stats_y1": stats_y1,
        "stats_y2": stats_y2,
        "swatch_rect": swatch_rect,
        "btn_rects": btn_rects,
        "footer_y": footer_y,
        "fonts": fonts
    }


def main():
    try:
        df = load_data(DATA_PATH)
    except Exception as e:
        print(f"Failed to load data: {e}")
        pygame.quit()
        sys.exit(1)

    engine = QuizEngine(df, NUM_CHOICES)
    question = engine.new_question()

    selected_index = None
    feedback_timer = 0
    running = True

    # Initial fonts and layout
    fonts = make_fonts(base_scale=WINDOW_H / 800.0)
    layout = compute_layout(WINDOW_W, WINDOW_H, NUM_CHOICES, fonts)

    while running:
        clock.tick(FPS)
        w, h = screen.get_size()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.VIDEORESIZE:
                pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                # Recompute fonts and layout on resize
                scale = max(0.8, min(1.2, event.h / 800.0))
                fonts = make_fonts(base_scale=scale)
                layout = compute_layout(event.w, event.h, NUM_CHOICES, fonts)

            # Mouse
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                for i, r in enumerate(layout["btn_rects"]):
                    if r.collidepoint(mx, my):
                        selected_index = i
                        chosen = question["options"][i]
                        engine.submit(chosen, question["correct_name"])
                        feedback_timer = int(0.9 * FPS)

            # Keyboard
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_1, pygame.K_KP_1): selected_index = 0
                elif event.key in (pygame.K_2, pygame.K_KP_2): selected_index = 1
                elif event.key in (pygame.K_3, pygame.K_KP_3): selected_index = 2
                elif event.key in (pygame.K_4, pygame.K_KP_4): selected_index = 3
                elif event.key == pygame.K_ESCAPE: running = False

                if selected_index is not None and 0 <= selected_index < NUM_CHOICES:
                    chosen = question["options"][selected_index]
                    engine.submit(chosen, question["correct_name"])
                    feedback_timer = int(0.9 * FPS)

        # Next question
        if feedback_timer > 0:
            feedback_timer -= 1
            if feedback_timer == 0:
                question = engine.new_question()
                selected_index = None

        # Draw
        screen.fill(BG)
        FONT_H1, FONT_H2, FONT_M, FONT_S = layout["fonts"]

        # Title
        draw_text(screen, "LEGO Colour Quiz", FONT_H1, TEXT, center=(w // 2, layout["header_y"]))

        # Stats (two lines)
        acc = (engine.score / engine.rounds * 100) if engine.rounds > 0 else 0.0
        draw_text(screen, f"Score: {engine.score}    Rounds: {engine.rounds}",
                  FONT_H2, TEXT_DIM, center=(w // 2, layout["stats_y1"]))
        draw_text(screen, f"Accuracy: {acc:.0f}%    Streak: {engine.streak}",
                  FONT_H2, TEXT_DIM, center=(w // 2, layout["stats_y2"]))

        # Prompt
        draw_text(screen, "Which LEGO colour is this?",
                  FONT_H2, TEXT, center=(w // 2, layout["swatch_rect"].y - int(FONT_H2.get_height() * 0.8)))

        # Swatch card
        rounded_rect(screen, layout["swatch_rect"], CARD, radius=16)
        inner = layout["swatch_rect"].inflate(-24, -24)
        swatch_color = hex_to_rgb_tuple(question["swatch_rgb"])
        rounded_rect(screen, inner, swatch_color, radius=12)
        rounded_rect(screen, layout["swatch_rect"], CARD_EDGE, radius=16, width=3)

        # Options
        mx, my = pygame.mouse.get_pos()
        for i, r in enumerate(layout["btn_rects"]):
            is_hover = r.collidepoint(mx, my)
            rounded_rect(screen, r, HOVER if is_hover else BTN, radius=14)
            rounded_rect(screen, r, CARD_EDGE, radius=14, width=2)

            label = f"{i+1}. {question['options'][i]}"
            # Ensure text fits: shrink font if necessary
            text_surface = FONT_M.render(label, True, TEXT)
            if text_surface.get_width() > r.width - 40:
                # Create a slightly smaller font for this line
                smaller = pygame.font.SysFont("arial", max(16, FONT_M.get_height() - 4))
                text_surface = smaller.render(label, True, TEXT)
            screen.blit(text_surface, (r.x + 20, r.y + (r.height - text_surface.get_height()) // 2))

            # Feedback borders
            if feedback_timer > 0 and engine.last_correct is not None:
                if question["options"][i] == engine.last_correct_name:
                    rounded_rect(screen, r, OK, radius=14, width=5)
                elif i == selected_index:
                    rounded_rect(screen, r, BAD, radius=14, width=5)

        # Footer
        draw_text(screen, "Click or press 1–4. ESC to quit.",
                  FONT_S, TEXT_DIM, center=(w // 2, layout["footer_y"]))

        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()
