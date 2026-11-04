import numpy as np

colors = {
    "Red": [
        (np.array([0, 100, 100]), np.array([10, 255, 255])),
        (np.array([170, 100, 100]), np.array([179, 255, 255]))
    ],
    "Green": [
        (np.array([35, 100, 100]), np.array([85, 255, 255]))
    ],
    "Blue": [
        (np.array([100, 100, 100]), np.array([140, 255, 255]))
    ]
}

for name, bound in colors.items():

    if name == "Red":
        print(f"red - {bound[0][0]} ---------- {bound[0][1]}")
        print(f"red - {bound[1][0]} ---------- {bound[1][1]}")

    else:
        print(f"{name} - {bound[0][0]} ---------- {bound[0][1]}")
        
    








