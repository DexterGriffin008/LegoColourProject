import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import colorsys

df = pd.read_csv("EPQ sanatised colours.csv No modulex.txt")

def hex_to_hsv(hex_str):
    r = int(hex_str[0:2], 16) / 255.0
    g = int(hex_str[2:4], 16) / 255.0
    b = int(hex_str[4:6], 16) / 255.0
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    return h * 360, s, v  # hue in degrees

df[['hue','saturation','value']] = df['rgb'].apply(lambda x: pd.Series(hex_to_hsv(x)))
df['y2'] = df['y2'].fillna(2025).astype(int)

# Define decades
decades = np.arange(1950, 2030, 5)

fig, axes = plt.subplots(2, len(decades)//2, subplot_kw={'polar':True}, figsize=(20,10))
axes = axes.flatten()

# Choose what sets line length: 'saturation' or 'value'
radius_col = 'saturation'

for ax, decade in zip(axes, decades):
    # Select colours active in this decade
    active = df[(df['y1'] <= decade+9) & (df['y2'] >= decade)]
    
    theta = np.deg2rad(active['hue'].values)
    radii = active[radius_col].values
    colors = ["#" + rgb for rgb in active['rgb']]
    
    # Plot each colour as a thin line
    for angle, radius, color in zip(theta, radii, colors):
        ax.plot([angle, angle], [0, radius], color=color, linewidth=5, alpha=0.9)
    
    ax.set_title(f"{decade}s", va='bottom')
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.set_xticks(np.deg2rad(np.arange(0,360,90)))
    ax.set_yticklabels([])

plt.suptitle(f"LEGO Colour Hue Lines by Decade (line length = {radius_col})", fontsize=16)
plt.tight_layout()
plt.show()
