"""Generate publication graphics from saved analysis only."""
import csv
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
R=Path(__file__).resolve().parents[1];O=R/'report/submission/graphics';O.mkdir(parents=True,exist_ok=True)
def read(n):
    with (R/'results/analysis/haiku'/n).open() as f:return list(csv.DictReader(f))
rates=read('summary_rates.csv');lens=read('lengths.csv');contrasts=read('contrasts.csv')
C={'zero':'#315A83','one':'#D28A32','few':'#148579'}
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.edgecolor':'#C0C8CE','text.color':'#172C3C','axes.labelcolor':'#172C3C','xtick.color':'#445866','ytick.color':'#445866','savefig.facecolor':'white'})
def save(fig,name):
    fig.savefig(O/(name+'.png'),dpi=300,bbox_inches='tight');fig.savefig(O/(name+'.pdf'),bbox_inches='tight');plt.close(fig)
fig,ax=plt.subplots(figsize=(9,2.65));ax.set(xlim=(0,10),ylim=(0,3));ax.axis('off')
boxes=[(.1,1.25,1.65,'12 reports','86 source items'),(2.1,1.25,2.15,'6 conditions','3 prompts × 2 lengths'),(4.65,1.25,2.25,'5 summary rounds','Only prior output continues'),(7.35,1.25,2.4,'Judge against original','Score rounds 1, 3 and 5')]
for x,y,w,a,b in boxes:
    ax.add_patch(FancyBboxPatch((x,y),w,1.1,boxstyle='round,pad=.08',facecolor='#EDF3F7',edgecolor='#B8CCD9',linewidth=1))
    ax.text(x+w/2,y+.73,a,ha='center',va='center',weight='bold',fontsize=9)
    ax.text(x+w/2,y+.32,b,ha='center',va='center',fontsize=8)
for x in (1.85,4.35,7.03):ax.add_patch(FancyArrowPatch((x,1.8),(x+.24,1.8),arrowstyle='-|>',mutation_scale=13,color='#546D7F'))
ax.text(1.6,.52,'360 generated summaries',ha='center',fontsize=10,weight='bold',color=C['zero'])
ax.text(5,.52,'216 scored summaries',ha='center',fontsize=10,weight='bold',color=C['few'])
ax.text(8.4,.52,'AI judge • no human audit',ha='center',fontsize=9)
save(fig,'design')

fig=plt.figure(figsize=(9,6.4));gs=fig.add_gridspec(2,2,height_ratios=[2.2,1],hspace=.65,wspace=.25)
for col,length in enumerate(('limited','free')):
    ax=fig.add_subplot(gs[0,col])
    for prompt in C:
        vals=[sum(float(x['rate']) for x in rates if x['prompt']==prompt and x['length']==length and x['round']==str(r))/12*100 for r in (1,3,5)]
        ax.plot((1,3,5),vals,color=C[prompt],marker={'zero':'o','one':'s','few':'D'}[prompt],linewidth=2,label={'zero':'Zero examples','one':'One pair','few':'Five pairs'}[prompt])
        dy=({'zero':-9,'few':9}.get(prompt,0) if length=='limited' else 0)
        ax.annotate(f'{vals[-1]:.1f}%',(5,vals[-1]),xytext=(7,dy),textcoords='offset points',va='center',color=C[prompt],fontsize=9)
    ax.set(xlim=(.8,6),ylim=(65,102),xticks=[1,3,5],xlabel='Summary round',ylabel='Items preserved (%)' if col==0 else '',title='A   250-word maximum' if col==0 else 'B   No length maximum')
    ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
    if col==0:ax.legend(loc='lower left',frameon=False,fontsize=8)
ax=fig.add_subplot(gs[1,:]);r=next(x for x in contrasts if x['length']=='limited' and x['round']=='5' and x['contrast']=='few-zero')
lo,hi,d=[100*float(r[k]) for k in ('low','high','difference')]
ax.axvline(0,color='#9AAAB4',ls='--',lw=1);ax.plot([lo,hi],[0,0],lw=3,color=C['few']);ax.scatter([d],[0],s=65,color=C['few'],zorder=3)
ax.set(ylim=(-.6,.6),xlim=(-12,12),yticks=[],xlabel='Five pairs minus zero examples (percentage points)')
ax.set_title(f'C   Primary contrast at round 5: {d:+.2f} pp  [95% CI {lo:+.2f}, {hi:+.2f}]',loc='left',fontsize=10,pad=8)
save(fig,'preservation')

fig,axs=plt.subplots(1,2,figsize=(9,3.2),sharey=True)
for ax,length in zip(axs,('limited','free')):
    for p in C:
        v=next(x for x in lens if x['length']==length and x['prompt']==p and x['round']=='5')
        y=sum(float(x['rate']) for x in rates if x['length']==length and x['prompt']==p and x['round']=='5')/12*100
        x=float(v['mean_words']);ax.scatter(x,y,s=80,color=C[p],marker={'zero':'o','one':'s','few':'D'}[p])
        ax.annotate({'zero':'Zero','one':'One pair','few':'Five pairs'}[p],(x,y),xytext=(6,8 if p!='few' else -16),textcoords='offset points',fontsize=9,color=C[p])
    ax.set(xlim=(100,800),ylim=(75,102),xlabel='Mean output length (words)',title='250-word maximum' if length=='limited' else 'No length maximum')
    ax.grid(alpha=.15);ax.set_axisbelow(True)
axs[0].set_ylabel('Items preserved at round 5 (%)')
fig.tight_layout();save(fig,'length_retention')
