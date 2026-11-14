"""Render figures from exported analysis tables; missing values remain missing."""
import argparse
import csv
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

COLORS = {'zero': '#7f7f7f', 'one': '#1f77b4', 'few': '#ff7f0e'}

def read(path):
    if not path.exists(): return []
    with path.open(encoding='utf-8', newline='') as stream: return list(csv.DictReader(stream))

def save(fig, out, name):
    fig.tight_layout()
    for ext in ('png', 'svg'): fig.savefig(out / f'{name}.{ext}', dpi=200)
    plt.close(fig)

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--analysis',required=True); parser.add_argument('--out',required=True)
    args=parser.parse_args(); root=Path(args.analysis); out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    primary=read(root/'primary.csv'); fig, ax=plt.subplots(figsize=(7,3.5)); plotted=0
    for row in primary:
        if not all(row.get(k) for k in ('difference','low','high')): continue
        diff, low, high=(float(row[k]) for k in ('difference','low','high'))
        ax.plot([low,high],[plotted,plotted],color='#ff7f0e'); ax.scatter([diff],[plotted],color='#ff7f0e'); plotted+=1
    labels=[r.get('model','') for r in primary if all(r.get(k) for k in ('difference','low','high'))]
    ax.set_yticks(range(plotted),labels); ax.axvline(0,color='black',linestyle='--'); ax.set_xlabel('Paired preservation difference (few − zero)'); ax.set_title('Primary contrast: limited, round 5')
    if not plotted: ax.text(.5,.5,'no data',transform=ax.transAxes,ha='center')
    save(fig,out,'primary_contrasts')
    for directory in sorted(p for p in root.iterdir() if p.is_dir() and p.resolve()!=out.resolve()):
        if not (directory/'summary_rates.csv').exists(): continue
        model=directory.name; rates=read(directory/'summary_rates.csv'); errors=read(directory/'errors.csv'); claims=read(directory/'claims.csv'); lengths=read(directory/'lengths.csv')
        fig, axes=plt.subplots(1,2,figsize=(10,4),sharey=True)
        for ax, length in zip(axes,('limited','free')):
            has=False
            for prompt,color in COLORS.items():
                ys=[]
                for rnd in (1,3,5):
                    vals=[float(r['rate']) for r in rates if r['length']==length and r['prompt']==prompt and int(r['round'])==rnd and r.get('rate')]
                    ys.append(sum(vals)/len(vals) if vals else float('nan'))
                if any(y==y for y in ys): ax.plot((1,3,5),ys,marker='o',label=prompt,color=color); has=True
            if not has: ax.text(.5,.5,'no data',transform=ax.transAxes,ha='center')
            ax.set(title=f'{model}: {length}',xlabel='Round',ylabel='Mean preservation rate',ylim=(0,1)); ax.set_xticks((1,3,5))
            if has: ax.legend()
        save(fig,out,f'trajectory_{model}')
        fig, axes=plt.subplots(1,2,figsize=(10,4),sharey=True)
        for ax,length in zip(axes,('limited','free')):
            subset=[r for r in errors if r['length']==length and r['round']=='5']; bottom=[0.,0.,0.]
            for label in ('preserved','omitted','strengthened','weakened','contradicted'):
                vals=[next((float(r['share']) for r in subset if r['prompt']==p and r['label']==label and r.get('share')),float('nan')) for p in COLORS]
                if subset: ax.bar(list(COLORS),vals,bottom=bottom,label=label); bottom=[b+(v if v==v else 0) for b,v in zip(bottom,vals)]
            if not subset: ax.text(.5,.5,'no data',transform=ax.transAxes,ha='center')
            ax.set(title=f'{model}: {length}, round 5',xlabel='Prompt',ylabel='Label share')
            if subset: ax.legend(fontsize=7)
        save(fig,out,f'errors_{model}')
        for table,name,column,ylabel in ((claims,'claims','mean_unsupported','Mean unsupported claims per summary'),(lengths,'lengths','mean_words','Mean words')):
            fig,axes=plt.subplots(1,2,figsize=(10,4),sharey=True)
            for ax,length in zip(axes,('limited','free')):
                has=False
                for prompt,color in COLORS.items():
                    subset=sorted((r for r in table if r['prompt']==prompt and r['length']==length and r.get(column)),key=lambda r:int(r['round']))
                    if subset: ax.plot([int(r['round']) for r in subset],[float(r[column]) for r in subset],marker='o',label=prompt,color=color); has=True
                if not has: ax.text(.5,.5,'no data',transform=ax.transAxes,ha='center')
                if name=='lengths' and length=='limited': ax.axhline(250,color='black',linestyle='--')
                ax.set(title=f'{model}: {length}',xlabel='Round',ylabel=ylabel)
                if has: ax.legend()
            save(fig,out,f'{name}_{model}')

if __name__=='__main__': main()
