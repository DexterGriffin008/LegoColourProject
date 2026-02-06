import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import colorsys

#Load dataset
df = pd.read_csv("EPQ sanatised colours.csv No modulex.txt")

#Convert RGB hex to HSV
def hex_to_hsv(hex_str):
    hex_str = hex_str.strip().lstrip("#")
    r = int(hex_str[0:2], 16) / 255.0
    g = int(hex_str[2:4], 16) / 255.0
    b = int(hex_str[4:6], 16) / 255.0
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    return h * 360, s, v

df[['hue','saturation','value']] = df['rgb'].apply(lambda x: pd.Series(hex_to_hsv(x)))
df['y2'] = df['y2'].fillna(2025).astype(int)

#Define 5-year intervals
intervals = [(start, start+4) for start in range(1950, 2026, 5)]

#Keep only intervals with active colours
valid_intervals = []
for start, end in intervals:
    active = df[(df['y1'] <= end) & (df['y2'] >= start)]
    if not active.empty:
        valid_intervals.append((start, end))

# --- Dynamic subplot grid ---
n = len(valid_intervals)
cols = 4
rows = int(np.ceil(n / cols))
fig, axes = plt.subplots(rows, cols, subplot_kw={'polar':True}, figsize=(6*cols, 5*rows))
axes = axes.flatten()

radius_col = 'saturation'

for ax, (start_year, end_year) in zip(axes, valid_intervals):
    active = df[(df['y1'] <= end_year) & (df['y2'] >= start_year)]
    
    theta = np.deg2rad(active['hue'].values)
    radii = active[radius_col].values
    colors = ["#" + rgb for rgb in active['rgb']]
    
    # Encode popularity
    linewidths = np.log1p(active['num_sets']) / 3
    alphas = np.clip(active['num_parts'] / active['num_parts'].max(), 0.3, 1)
    
    for angle, radius, color, lw, a in zip(theta, radii, colors, linewidths, alphas):
        ax.plot([angle, angle], [0, radius], color=color, linewidth=lw, alpha=a)
    
    # Highlight new colours
    new_colours = active[active['y1'].between(start_year, end_year)]
    ax.scatter(np.deg2rad(new_colours['hue']), new_colours[radius_col],
               c=["#" + rgb for rgb in new_colours['rgb']], s=50, edgecolor="black", zorder=5)
    
    # Styling
    ax.set_title(f"{start_year}-{end_year}", va='bottom', fontsize=14, fontweight="bold")
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.set_xticks(np.deg2rad([0,90,180,270]))
    ax.set_xticklabels(["Red","Yellow","Green","Blue"], fontsize=11)
    ax.set_yticklabels([])
    ax.grid(False)

# Hide unused axes
for ax in axes[len(valid_intervals):]:
    ax.set_visible(False)

plt.suptitle("LEGO Colour Hue Lines by 5-Year Interval\nLine length = saturation, width = num_sets, opacity = num_parts",
             fontsize=22, y=1.02, fontweight="bold")
plt.subplots_adjust(top=0.9, wspace=0.35, hspace=0.5)
plt.show()
