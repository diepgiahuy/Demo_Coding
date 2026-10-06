import math
import random

SEED = 2706
V_ROADS = [(-108,8),(-72,8),(-36,8),(0,16),(36,8),(72,8),(108,8)]
H_ROADS = [(-112,8),(-80,8),(-48,8),(-16,8),(16,8),(48,8),(80,8),(112,8)]


def intervals_from_roads(roads):
    out=[]
    for (c0,w0),(c1,w1) in zip(roads[:-1], roads[1:]):
        a=c0+w0/2
        b=c1-w1/2
        if b>a:
            out.append((a,b))
    return out

X_BLOCKS=intervals_from_roads(V_ROADS)
Y_BLOCKS=intervals_from_roads(H_ROADS)


def detail_level(cx, cy):
    d=math.hypot(cx-70, cy+95)
    if d<100: return 2
    if d<180: return 1
    return 0


def build_plan(seed=SEED):
    rng=random.Random(seed)
    blocks=[]
    parcels=[]
    buildings=[]
    for iy,(y0,y1) in enumerate(Y_BLOCKS):
        for ix,(x0,x1) in enumerate(X_BLOCKS):
            block_id=f'BLK_{ix}_{iy}'
            blocks.append({'id':block_id,'bounds':[x0,x1,y0,y1]})
            if (x1-x0)>=(y1-y0):
                xm=(x0+x1)/2
                splits=[(x0,xm,y0,y1),(xm,x1,y0,y1)]
            else:
                ym=(y0+y1)/2
                splits=[(x0,x1,y0,ym),(x0,x1,ym,y1)]
            for pi,p in enumerate(splits):
                parcel_id=f'PAR_{ix}_{iy}_{pi}'
                parcels.append({'id':parcel_id,'block_id':block_id,'bounds':list(p),'land_use':'occupied'})
                pcx=(p[0]+p[1])/2; pcy=(p[2]+p[3])/2
                detail=detail_level(pcx,pcy)
                depth=(pcy-Y_BLOCKS[0][0])/max(1,(Y_BLOCKS[-1][1]-Y_BLOCKS[0][0]))
                if depth>0.70 and rng.random()<0.38:
                    floors=rng.randint(9,16)
                elif depth>0.50:
                    floors=rng.randint(5,10)
                else:
                    floors=rng.randint(3,7)
                setback=1.0 if detail>=1 else 0.7
                bx0,bx1=p[0]+setback,p[1]-setback
                by0,by1=p[2]+setback,p[3]-setback
                buildings.append({
                    'id':f'B_{ix}_{iy}_{pi}',
                    'parcel_id':parcel_id,
                    'parcel_bounds':list(p),
                    'footprint':[bx0,bx1,by0,by1],
                    'floors':floors,
                    'detail':detail,
                    'material_index':rng.randrange(6 if detail else 3),
                })
    return {'seed':seed,'roads':{'vertical':V_ROADS,'horizontal':H_ROADS},'blocks':blocks,'parcels':parcels,'buildings':buildings}


def validate_plan(plan):
    issues=[]
    parcel_by_id={p['id']:p for p in plan['parcels']}
    building_by_parcel={}
    for b in plan['buildings']:
        building_by_parcel.setdefault(b['parcel_id'],[]).append(b)
        p=parcel_by_id[b['parcel_id']]['bounds']
        f=b['footprint']
        if not (p[0] <= f[0] < f[1] <= p[1] and p[2] <= f[2] < f[3] <= p[3]):
            issues.append(f"overflow:{b['id']}")
        if (f[1]-f[0]) <= 0 or (f[3]-f[2]) <= 0:
            issues.append(f"invalid_footprint:{b['id']}")
    for p in plan['parcels']:
        if p['land_use']=='occupied' and len(building_by_parcel.get(p['id'],[])) != 1:
            issues.append(f"occupancy:{p['id']}:{len(building_by_parcel.get(p['id'],[]))}")
    return {
        'ok': not issues,
        'issues': issues,
        'block_count':len(plan['blocks']),
        'parcel_count':len(plan['parcels']),
        'building_count':len(plan['buildings']),
        'empty_parcels':sum(1 for p in plan['parcels'] if p['land_use']=='occupied' and p['id'] not in building_by_parcel),
        'overflow_count':sum(1 for x in issues if x.startswith('overflow:')),
    }

if __name__=='__main__':
    import json
    p=build_plan()
    r=validate_plan(p)
    print(json.dumps(r,indent=2))
    assert r['ok']
    assert r['block_count']==42
    assert r['parcel_count']==84
    assert r['building_count']==84
    print('CITY_PLAN_PROOF_PASS')
