"""Generate public GitHub profile graphics without external Python dependencies."""
import os, json, urllib.request, math
from collections import Counter
from pathlib import Path
from xml.sax.saxutils import escape

OUT = Path('assets/generated')
BG='#101925'; BORDER='#2b415d'; TEXT='#e5efff'; MUTED='#92a9c5'; BLUE='#6ec7ff'
COLORS=['#1a293b','#244567','#32649a','#438bde','#82cbff']
DUR=36

def api(query, variables):
    req=urllib.request.Request('https://api.github.com/graphql', data=json.dumps({'query':query,'variables':variables}).encode(), headers={'Authorization':'Bearer '+os.environ['GITHUB_TOKEN'],'Content-Type':'application/json','User-Agent':'zgAllin-profile'})
    with urllib.request.urlopen(req, timeout=45) as res: data=json.load(res)
    if data.get('errors'): raise RuntimeError(str(data['errors']))
    return data['data']['user']

def get_data(login):
    user=api('''query($login:String!){user(login:$login){repositories(privacy:PUBLIC, ownerAffiliations:[OWNER], isFork:false){totalCount} contributionsCollection {totalCommitContributions totalPullRequestContributions totalIssueContributions totalPullRequestReviewContributions contributionCalendar {totalContributions weeks {contributionDays {weekday contributionCount date}}}}}}''',{'login':login})
    langs=Counter(); stars=0; cursor=None
    while True:
        r=api('''query($login:String!, $after:String){user(login:$login){repositories(first:50,after:$after,privacy:PUBLIC,ownerAffiliations:[OWNER],isFork:false){pageInfo{hasNextPage endCursor} nodes{stargazerCount languages(first:20,orderBy:{field:SIZE,direction:DESC}){edges{size node{name}}}}}}}''',{'login':login,'after':cursor})['repositories']
        for repo in r['nodes']:
            stars+=repo['stargazerCount']
            for edge in repo['languages']['edges']: langs[edge['node']['name']]+=edge['size']
        if not r['pageInfo']['hasNextPage']: break
        cursor=r['pageInfo']['endCursor']
    return user,langs,stars

def svg(w,h,body,title):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img"><title>{escape(title)}</title><style>text{{font-family:Arial,Helvetica,sans-serif}} .mono{{font-family:monospace;letter-spacing:1.5px}}</style>{body}</svg>'
def text(x,y,s,size=14,color=TEXT,weight=400,extra=''):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-weight="{weight}" {extra}>{escape(str(s))}</text>'
def panel(w,h):
    return f'<rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="15" fill="{BG}" stroke="{BORDER}"/>'
def level(n,m):
    return 0 if not n else min(4,max(1,math.ceil(4*n/max(1,m))))
def write(name,data):
    OUT.mkdir(parents=True,exist_ok=True); (OUT/name).write_text(data,encoding='utf-8')

def metrics(user,langs,stars):
    c=user['contributionsCollection']; cal=c['contributionCalendar']; w,h=920,300
    b=panel(w,h)+text(27,34,'DEVELOPER METRICS',12,BLUE,700,'class="mono"')+text(27,56,'GitHub-visible activity / rolling year',12,MUTED)
    vals=[('Contributions',cal['totalContributions']),('Commits',c['totalCommitContributions']),('Pull requests',c['totalPullRequestContributions']),('Reviews',c['totalPullRequestReviewContributions']),('Public repos',user['repositories']['totalCount']),('Repository stars',stars)]
    for i,(label,num) in enumerate(vals):
        x=27+(i%3)*145; y=79+(i//3)*88
        b+=f'<rect x="{x}" y="{y}" width="133" height="74" rx="8" fill="#152238"/>'+text(x+12,y+32,f'{num:,}',27,TEXT,700)+text(x+12,y+55,label,11,MUTED)
    b+=text(490,34,'LANGUAGE FOOTPRINT',12,BLUE,700,'class="mono"')+text(490,56,'Public owned non-fork repositories / by bytes',11,MUTED)
    total=sum(langs.values())
    for i,(name,n) in enumerate(langs.most_common(5)):
        y=84+i*36; p=n/total if total else 0
        b+=text(490,y,name,12)+text(887,y,f'{p:.1%}',12,MUTED,extra='text-anchor="end"')+f'<rect x="490" y="{y+7}" width="397" height="5" rx="2.5" fill="#25354b"/><rect x="490" y="{y+7}" width="{397*p:.2f}" height="5" rx="2.5" fill="{["#78caff","#5087ff","#7d91e6","#54a9b8","#7b9cbd"][i]}"/>'
    if not total: b+=text(490,100,'No language data available.',13,MUTED)
    b+=text(27,270,'Public repository totals are all-time; activity counts use the rolling contribution window.',11,MUTED)+text(490,270,'Top 20 languages per repository; size is not proficiency.',11,MUTED)
    write('metrics.svg',svg(w,h,b,'GitHub developer metrics'))

def calendar_data(user):
    weeks=user['contributionsCollection']['contributionCalendar']['weeks']; days={(x,d['weekday']):d['contributionCount'] for x,week in enumerate(weeks) for d in week['contributionDays']}; return weeks,days,max(days.values(),default=1)

def iso(user):
    weeks,days,m=calendar_data(user); w,h=920,280; b=panel(w,h)+text(27,33,'CONTRIBUTIONS / ISOMETRIC',12,BLUE,700,'class="mono"')+text(27,55,'Rolling year · height represents daily activity',12,MUTED)
    # Projection: horizontal weeks, diagonal weekdays, vertical count.
    for (x,y),n in sorted(days.items(),key=lambda kv:(kv[0][1],kv[0][0])):
        px=48+x*14+y*8; py=151+y*8-x*.65; z=2+(math.log1p(n)/math.log1p(max(1,m)))*77 if n else 2
        top=COLORS[level(n,m)]; side='#29476b' if n else '#132034'; front='#37628e' if n else '#19283b'; a=11; d=7; py-=z
        b+=f'<g><title>{weeks[x]["contributionDays"][next(i for i,v in enumerate(weeks[x]["contributionDays"]) if v["weekday"]==y)]["date"]}: {n} contributions</title><path d="M{px},{py} l{a},-1 {d},5 -{a},1 Z" fill="{top}"/><path d="M{px},{py} l{d},5 0,{z:.2f} -{d},-5 Z" fill="{side}"/><path d="M{px+d},{py+5} l{a},-1 0,{z:.2f} -{a},1 Z" fill="{front}"/></g>'
    b+=text(27,250,'Less',11,MUTED)
    for i,c in enumerate(COLORS): b+=f'<rect x="{61+i*18}" y="239" width="13" height="13" rx="2" fill="{c}"/>'
    b+=text(157,250,'More',11,MUTED)+text(892,250,'GitHub contribution calendar',11,MUTED,extra='text-anchor="end"')
    write('contributions-3d.svg',svg(w,h,b,'3D contribution calendar'))

def snake(user):
    weeks,days,m=calendar_data(user); w,h=920,190; step=15; x0=38; y0=61; cols=len(weeks)
    b=panel(w,h)+text(27,30,'CONTRIBUTION SNAKE',12,BLUE,700,'class="mono"')
    # Walk all weeks in a continuous serpentine path. Every visited square fades.
    coords=[(x,y) for y in range(7) for x in (range(cols) if y%2==0 else range(cols-1,-1,-1))]
    points=[(x0+x*step,y0+y*step) for x,y in coords]; path='M '+' L '.join(f'{x} {y}' for x,y in points); length=(len(points)-1)*step; travel=.94
    for i,(x,y) in enumerate(coords):
        if (x,y) not in days: continue
        n=days[(x,y)]; t=i/(len(coords)-1)*travel; end=min(.97,t+.006)
        times=f'0;{t:.6f};{end:.6f};1' if i else f'0;{end:.6f};1'
        vals='1;1;.15;.15' if i else '1;.15;.15'
        b+=f'<rect x="{x0+x*step-5}" y="{y0+y*step-5}" width="10" height="10" rx="2" fill="{COLORS[level(n,m)]}"><animate attributeName="opacity" values="{vals}" keyTimes="{times}" dur="{DUR}s" repeatCount="indefinite"/></rect>'
    tail=48
    b+=f'<path d="{path}" fill="none" stroke="#52b7f5" stroke-width="7" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="{tail} {length+tail}" stroke-dashoffset="{tail}"><animate attributeName="stroke-dashoffset" values="{tail};{-length+tail};{-length+tail}" keyTimes="0;{travel};1" dur="{DUR}s" repeatCount="indefinite"/></path>'
    b+=f'<circle r="5.2" fill="#c2ecff" stroke="#62b9ff" stroke-width="1.2"><animateMotion path="{path}" dur="{DUR}s" calcMode="linear" keyPoints="0;1;1" keyTimes="0;{travel};1" repeatCount="indefinite"/></circle>'
    b+=text(27,175,'One loop through the visible contribution calendar.',11,MUTED)+text(890,175,'zgAllin / 19',11,MUTED,extra='text-anchor="end"')
    write('snake.svg',svg(w,h,b,'Animated contribution snake'))

def main():
    u,l,s=get_data(os.environ['PROFILE_USER']); metrics(u,l,s); iso(u); snake(u)
if __name__=='__main__': main()
