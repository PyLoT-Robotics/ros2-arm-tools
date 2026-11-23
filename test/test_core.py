import pytest
from arm_tools.core import ArmProfile,trajectory_values
from arm_tools.store import PoseStore
P={'shoulder':{'min':-1.,'max':1.},'slide':{'type':'prismatic','min':0.,'max':.1}}


def test_capture_reorders_and_jog_is_in_si_units():
    p=ArmProfile(P);current=p.capture(['slide','shoulder','other'],[.05,.2,100.])
    assert p.jog(current,'shoulder',.1)['shoulder']==pytest.approx(.3)
    assert trajectory_values(p,current,2.)==(['shoulder','slide'],[.2,.05],2.)


@pytest.mark.parametrize('pose',[{'shoulder':0.},{'shoulder':2.,'slide':.05},{'shoulder':float('nan'),'slide':.05},{'shoulder':True,'slide':.05}])
def test_invalid_targets_rejected(pose):
    with pytest.raises(ValueError):ArmProfile(P).validate(pose)


def test_jog_refuses_limit_crossing_and_missing_state():
    p=ArmProfile(P)
    with pytest.raises(ValueError):p.jog({'shoulder':.9,'slide':.05},'shoulder',.2)
    with pytest.raises(ValueError):p.capture(['shoulder'],[0.])
    with pytest.raises(ValueError):p.capture(['shoulder','shoulder'],[0.,0.])


@pytest.mark.parametrize('duration',[0.,-1.,float('inf')])
def test_bad_duration(duration):
    with pytest.raises(ValueError):trajectory_values(ArmProfile(P),{'shoulder':0.,'slide':0.},duration)


def test_store_roundtrip_refuses_overwrite_and_corruption(tmp_path):
    path=tmp_path/'poses.yaml';s=PoseStore(path);pose={'shoulder':.1,'slide':.05}
    s.put('ready',pose);assert s.get('ready')==pose
    with pytest.raises(ValueError):s.put('ready',pose)
    path.write_text('broken')
    with pytest.raises(ValueError):s.put('ready',pose,True)
    assert path.read_text()=='broken'
