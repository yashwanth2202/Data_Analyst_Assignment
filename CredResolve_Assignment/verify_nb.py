import json, sys
sys.stdout.reconfigure(encoding='utf-8')
with open('analysis_notebook.ipynb') as f:
    nb = json.load(f)
cells = nb['cells']
print('Total cells:', len(cells))
viz_cells = 0
for i, cell in enumerate(cells):
    src = ''.join(cell['source'])
    has_plot = 'plt.show()' in src
    if has_plot:
        viz_cells += 1
    ct = cell['cell_type']
    snippet = src[:65].replace('\n', ' ')
    marker = ' [VIZ]' if has_plot else ''
    print(f'  Cell {i:02d} [{ct}]{marker}: {snippet}')
print()
print('Visualization cells:', viz_cells)
