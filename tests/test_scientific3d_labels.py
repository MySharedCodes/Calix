import base64
import json
from pathlib import Path
import pytest
from backend.engine import Engine
from backend.syntax import InputError


def test_labels_keep_assignment_and_quantity_values():
    engine=Engine()
    result=engine.execute('v=1[m/s];Column[{Labeled[v,"velocity,x"],Labeled[2+3,"sum"]}]')
    assert result['items'][0]['label']=='velocity,x'
    assert result['items'][0]['text']=='1[m / s]'
    assert result['items'][1]['text']=='5'
    assert engine.execute('v*2[s]')['text']=='2[m]'
    assert engine.execute('Table[a=k+1; a^2,{k,1,3}]')['text']=='{4, 9, 16}'
    assert engine.execute('(a=2;a+3)*2')['text']=='10'
    assert engine.execute('Labeled[Plot[x,{x,0,1}],"position"]')['label']=='position'
    for code in ('Labeled[1,2]','Labeled[1,""]','Labeled[1]'):
        with pytest.raises(InputError): engine.execute(code)


def test_volume_order_quantization_and_native_sampling():
    result=Engine().execute('DensityPlot3D[1+x+2*y+3*z,{x,0,1},{y,0,1},{z,0,1},PlotPoints->17]')
    data=base64.b64decode(result['volume'])
    assert len(data)==17**3 and result['density_max']==7
    assert data[0]==round(255*(1/7)**0.5)
    assert data[16]==round(255*(2/7)**0.5)
    assert data[16*17]==round(255*(3/7)**0.5)
    assert data[16*17**2]==round(255*(4/7)**0.5)
    assert data[-1]==255 and 'C++' in result['engine']


@pytest.mark.parametrize('code',[
    'DensityPlot3D[x,{x,-1,1},{y,-1,1},{z,-1,1}]',
    'DensityPlot3D[0,{x,-1,1},{y,-1,1},{z,-1,1}]',
    'DensityPlot3D[1,{x,1,0},{y,-1,1},{z,-1,1}]',
    'DensityPlot3D[1,{x,0,1},{x,-1,1},{z,-1,1}]',
    'DensityPlot3D[1,{x,0,1},{y,-1,1},{z,-1,1},PlotPoints->1000]',
    'Graphics3D[{Arrow[{{0,0,0}}]}]',
    'Graphics3D[{Point[{Infinity,0,0}]}]',
    'Graphics3D[{Style[Point[{0,0,0}],"red"]}]',
])
def test_invalid_scientific_graphics(code):
    with pytest.raises(InputError): Engine().execute(code)


def test_only_complete_case_notebooks_have_output_labels():
    from scripts.example_annotations import split
    authored = {json.loads(Path('frontend/src/starter.json').read_text(encoding='utf-8'))['title']}
    authored.update(n['title'] for n in json.loads(Path('frontend/src/example-notebooks.json').read_text(encoding='utf-8')))
    for path in Path('examples').glob('*.calix'):
        notebook=json.loads(path.read_text(encoding='utf-8'))
        for cell in notebook['cells']:
            if cell['mode']=='markdown': continue
            if notebook['title'] not in authored:
                assert 'Labeled[' not in cell['code'], path
                continue
            output=split(cell['code'],';')[-1].strip()
            assert not output or output.startswith(('Labeled[','Column[')), (path,output)
