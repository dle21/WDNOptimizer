from NetworkVisualizer import NetworkVisualizer
import os

# nwkv = NetworkVisualizer('TONGALA_Calibration_2022.inp')
# nwkv.generate_gdfs()
# nwkv.export_shp()

# nwkv = NetworkVisualizer('OPTION_2___TONGALA_Masterplanning_2043_Horizon__1.inp')
# nwkv.generate_gdfs()
# # nwkv.plot_network()
# nwkv.draw_comparison([os.path.join('non-dominated solutions', f) for f in os.listdir('non-dominated solutions') if os.path.splitext(f)[-1] == '.inp'])
# nwkv.export_shp()
# nwkv.plot_network()

files = [os.path.join('non-dominated solutions', f) for f in os.listdir('non-dominated solutions') if os.path.splitext(f)[-1] == '.inp']
import matplotlib.pyplot as plt

for cluster in [0, 1, 2, 3]:
    costs = [float(f.split('_')[1]) for f in files if int(f.split('_')[-3]) == cluster]
    penalties = [float(f.split('_')[3].strip('.inp')) for f in files if int(f.split('_')[-3]) == cluster]
    plt.scatter(costs, penalties)
plt.show()