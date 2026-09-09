"""Manual Windows render/performance regression check, isolated from user data.
Run: .venv/Scripts/python.exe tests/verify_hologram.py
"""
import sys
import tempfile
import time
import statistics
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.assistant import Assistant
from core.config import load_config
from ui.desktop import Desktop
from ui.theme import BG, GLOW
from ui.widgets.hologram import sphere_segments
from tests.verify_v2_gui import pump, capture
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]

def main():
    with tempfile.TemporaryDirectory() as temp:
        config, _ = load_config(Path(temp))
        config['tts']['enabled'] = False
        config['desktop']['startup_greeting'] = False
        d = Desktop(Assistant(Path(temp), config), integrations=False)
        errors = []
        d.root.report_callback_exception = lambda *error: errors.append(str(error))
        try:
            d.root.geometry('1440x880+10+10')
            pump(d, .5)
            core = d.core
            count = len(core.find_all())
            frames, costs = [], []
            for state, mic in [('Idle',False), ('Idle',True), ('Listening',True), ('Processing',True), ('Speaking',True), ('Error',True), ('Offline',False)]:
                for _ in range(90):
                    start = time.perf_counter()
                    core.tick(1/30, state, .75 if state == 'Listening' else 0, mic)
                    costs.append((time.perf_counter()-start)*1000)
                before = core.coords(core.mesh[0])
                core.tick(.1, state, .75, mic)
                assert before != core.coords(core.mesh[0]), state+' is static'
                assert len(core.find_all()) == count, 'Canvas items leak across frames'
                d.state_label.configure(text='STANDBY' if not mic and state == 'Idle' else state.upper())
                d.waveform.tick(state, .75, .1, core.elapsed)
                d.root.update_idletasks()
                name = 'hologram-'+('standby' if not mic and state == 'Idle' else state.lower())+'.png'
                capture(d.root, name)
                frame = Image.open(ROOT/'data'/name)
                # Window-only crop of the observed Tk core rectangle.
                x = core.winfo_rootx()-d.root.winfo_rootx()
                y = core.winfo_rooty()-d.root.winfo_rooty()
                crop = frame.crop((x,y,x+core.winfo_width(),y+core.winfo_height()))
                crop.thumbnail((430,360))
                frames.append((name,crop.copy()))
            # Verify measured input amplitude produces a larger listening response.
            for _ in range(60): core.tick(1/30,'Listening',0,True)
            quiet = core.reaction
            for _ in range(60): core.tick(1/30,'Listening',.9,True)
            assert core.reaction > quiet+.7
            # Geometry must remain spherical through rotation, with true depth.
            for segment in sphere_segments():
                for x,y,z in segment:
                    assert abs(x*x+y*y+z*z-1) < 1e-9
            assert core.transform(0,0,1)[2] > core.transform(0,0,-1)[2]
            colors = {core.itemcget(item,'fill') for item in core.mesh}
            assert len(colors) > 8, 'Mesh has lost front/back shading'
            core.intensity = 0
            core.tick(.1,'Idle',0,True)
            frozen = core.elapsed
            core.tick(.1,'Idle',0,True)
            assert core.elapsed == frozen
            core.intensity = .7
            for size in ('1060x630','1280x680','1840x980','2480x1340'):
                print('Checking layout', size, flush=True)
                d.root.geometry(size)
                pump(d,.3)
                for widget in (d.entry,d.mic_button,d.graph,d.output,*d.media_controls.winfo_children()):
                    assert widget.winfo_ismapped(), (size,str(widget))
                    assert widget.winfo_rooty()+widget.winfo_height() <= d.root.winfo_rooty()+d.root.winfo_height(), (size,str(widget))
                    assert widget.winfo_rootx()+widget.winfo_width() <= d.root.winfo_rootx()+d.root.winfo_width(), (size,str(widget))
                assert d.graph.winfo_height() >= 30, (size,d.graph.winfo_height())
                if size == '1060x630': capture(d.root, 'hologram-compact.png')
            # Hidden windows must stop geometry updates, then resume on return.
            d.root.withdraw()
            pump(d,.6)
            hidden_elapsed = core.elapsed
            pump(d,.6)
            assert core.elapsed == hidden_elapsed, 'Hidden hologram is still rendering'
            d.root.deiconify()
            pump(d,.7)
            assert core.elapsed > hidden_elapsed, 'Projection did not resume after restore'
            assert not errors, errors
            sheet = Image.new('RGB',(430*4,400*2),BG)
            draw = ImageDraw.Draw(sheet)
            for i,(name,frame) in enumerate(frames):
                x,y = (i%4)*430,(i//4)*400
                draw.text((x+15,y+12),name.removeprefix('hologram-').removesuffix('.png').upper(),fill=GLOW)
                sheet.paste(frame,(x,y+35))
            sheet.save(ROOT/'data/hologram-states.png')
            print(f'PASS: all states move; amplitude response; spherical depth; no item growth ({count} items); zero-intensity freeze; four layouts; hidden-window pause/resume; no callback errors.')
            print(f'Render tick: median {statistics.median(costs):.2f} ms; p95 {sorted(costs)[int(len(costs)*.95)]:.2f} ms; max {max(costs):.2f} ms.')
        finally:
            d.close()

if __name__ == '__main__': main()
