"""Blueprint 3D projection using cached geometry and a persistent Tk Canvas scene.

Short mesh segments, orbital trails and particles are depth-sorted each frame.
Pillow creates transparent glow sprites only on debounced resize. This widget
consumes presentation state; it never starts audio or routes commands.
"""
from dataclasses import dataclass
from functools import lru_cache
import math
import tkinter as tk
from PIL import Image, ImageDraw, ImageFilter, ImageTk
from ui.theme import PANEL, CYAN, GLOW, MUTED, AMBER, WARM

HOT = '#fff0b5'


@dataclass(frozen=True)
class Motion:
    speed: float
    brightness: float
    expansion: float
    waves: float


PROFILES = {
    'Idle': Motion(.36, .95, 1., .24),
    'Listening': Motion(.8, 1.12, 1.04, .8),
    'Processing': Motion(1.8, 1.05, .86, .48),
    'Speaking': Motion(1.05, 1.22, 1.07, 1.),
    'Error': Motion(.24, .86, .96, .5),
    'Offline': Motion(.12, .67, .96, .10),
}


def appearance(state, mic_active):
    return PROFILES['Offline'] if state == 'Idle' and not mic_active else PROFILES.get(state, PROFILES['Idle'])


@lru_cache(maxsize=1024)
def _blend(color, step):
    strength = step/127
    return '#' + ''.join(f'{round(int(PANEL[i:i+2],16)*(1-strength)+int(color[i:i+2],16)*strength):02x}' for i in (1,3,5))


def mix(color, strength):
    return _blend(color, round(max(0., min(1., strength))*127))


def voice_envelope(t):
    """Synthetic syllables gated by real SAPI busy state, not measured TTS audio."""
    return (.5+.5*math.sin(t*7.8+.6*math.sin(t*2.3)))*(.65+.35*math.sin(t*1.9)**2)


class SmoothMotion:
    def __init__(self):
        for key in ('speed', 'brightness', 'expansion', 'waves'):
            setattr(self, key, getattr(PROFILES['Idle'], key))

    def approach(self, target, dt, rate=5.):
        weight = 1-math.exp(-max(0., dt)*rate)
        for key in ('speed', 'brightness', 'expansion', 'waves'):
            value = getattr(self, key)
            setattr(self, key, value+(getattr(target, key)-value)*weight)


def sphere_segments():
    """True unit sphere: meridians and latitudes split for depth-based shading."""
    circles = []
    for i in range(12):
        longitude = i*math.pi/12
        circles.append([(math.cos(a)*math.cos(longitude), math.sin(a),
                         math.cos(a)*math.sin(longitude))
                        for a in (j*math.tau/48 for j in range(49))])
    for i in range(1, 10):
        latitude = -math.pi/2+i*math.pi/10
        circles.append([(math.cos(a)*math.cos(latitude), math.sin(latitude),
                         math.sin(a)*math.cos(latitude))
                        for a in (j*math.tau/48 for j in range(49))])
    return [circle[start:start+13] for circle in circles for start in (0,12,24,36)]


class AICore(tk.Canvas):
    def __init__(self, parent):
        super().__init__(parent, bg=PANEL, highlightthickness=0, width=400, height=100)
        self.phase = self.elapsed = self.audio = self.reaction = self.energy = 0.
        self.intensity, self.radius = .7, 1.
        self.state, self.mic_active = 'Idle', False
        self.ready, self.last_style, self.resize_job = False, None, None
        self.motion = SmoothMotion()
        self.geometry = sphere_segments()
        self.bind('<Configure>', self.schedule_resize)
        self.bind('<Destroy>', self._destroyed, add='+')

    def _destroyed(self, event):
        if event.widget is self and self.resize_job:
            self.after_cancel(self.resize_job)
            self.resize_job = None

    def schedule_resize(self, _=None):
        if self.resize_job: self.after_cancel(self.resize_job)
        self.resize_job = self.after(90, self.rebuild)

    def bloom(self, size, color, strength, node=False):
        """Transparent radiance; no opaque rectangles over the mesh."""
        layer = Image.new('RGBA', (size, size))
        draw = ImageDraw.Draw(layer)
        rgb = tuple(int(color[i:i+2],16) for i in (1,3,5))
        mid = size/2
        for i in range(48,0,-1):
            rr = size*i/100
            alpha = min(255, int((1-i/50)**2*(240 if node else 92)*strength))
            draw.ellipse((mid-rr,mid-rr,mid+rr,mid+rr), fill=(*rgb,alpha))
        layer = layer.filter(ImageFilter.GaussianBlur(max(1, size/65)))
        return ImageTk.PhotoImage(layer, master=self)

    def rebuild(self):
        self.resize_job = None
        self.ready = False
        self.delete('all')
        w,h = self.winfo_width(),self.winfo_height()
        if w < 20 or h < 20: return
        self.cx,self.cy = w/2,h/2-2
        self.radius = max(16,min((w-38)/2.75,(h-48)/2.65))
        r = self.radius
        self.blooms = {}
        for key,color,strength in [('dim',CYAN,.75),('normal',CYAN,1.1),('bright',GLOW,1.5),('error',AMBER,.85)]:
            self.blooms[key] = self.bloom(max(48,int(r*2.55)),color,strength)
            self.blooms[key+'-node'] = self.bloom(max(32,int(r*.72)),color,strength,True)
        self.glow = self.create_image(self.cx,self.cy,image=self.blooms['dim'])
        self.create_line(self.cx, self.cy-r*1.19,self.cx,self.cy+r*1.26,
                         fill=mix(CYAN,.18),dash=(2,6))
        for side in (-1,1):
            x = self.cx+side*r*1.25
            self.create_line(x,self.cy-r*.65,x,self.cy+r*.65,fill=mix(CYAN,.17),dash=(1,4))
            self.create_line(x-side*8,self.cy,x+side*8,self.cy,fill=mix(CYAN,.4))
        self.emitter = [self.create_oval(0,0,1,1,outline=CYAN) for _ in range(6)]
        self.cap = [self.create_oval(0,0,1,1,outline=CYAN) for _ in range(3)]
        self.beams = [self.create_line(0,0,1,1,fill=CYAN) for _ in range(5)]
        self.ring_arcs = [self.create_arc(0,0,1,1,style='arc',outline=CYAN,
                                        width=3 if i%4 == 0 else 1) for i in range(16)]
        self.mesh = [self.create_line(0,0,1,1,fill=GLOW) for _ in self.geometry]
        self.orbits = [self.create_line(0,0,1,1,fill=GLOW,width=1.5) for _ in range(36)]
        self.orbit_heads = [self.create_oval(0,0,1,1,fill=HOT,outline=CYAN,width=2) for _ in range(3)]
        self.nodes = [self.create_oval(0,0,1,1,fill=GLOW,outline='') for _ in range(100)]
        self.inner_glow = self.create_image(self.cx,self.cy,image=self.blooms['dim-node'])
        self.nucleus = [self.create_oval(0,0,1,1,outline=GLOW,fill='') for _ in range(4)]
        self.scans = [self.create_line(0,0,1,1,fill=CYAN) for _ in range(5)]
        self.resonance = [self.create_line(0,0,1,1,fill=CYAN) for _ in range(4)]
        self.caption = self.create_text(w/2,h-10,text='',fill=MUTED,font=('Consolas',8))
        self.create_text(8,12,text='AI CORE / 3D PROJECTION' if w>380 else 'AI CORE / 3D',fill=MUTED,font=('Consolas',8),anchor='nw')
        self.signal = self.create_text(w-8,12,text='',fill=GLOW,font=('Consolas',8),anchor='ne')
        self.annotations = []
        if w/2-r*1.30 > 100 and h > 340:
            for text,side,y in [('PARTICLE SHELL',-1,-.55),('ROTATING MESH',1,-.35),('ENERGY NODE',1,.15)]:
                x = self.cx+side*r*1.02
                end = self.cx+side*r*1.30
                self.annotations.append(self.create_line(x,self.cy+y*r,end,self.cy+(y-.07)*r,fill=mix(CYAN,.35)))
                self.annotations.append(self.create_text(end,self.cy+(y-.12)*r,text=text,fill=MUTED,
                                         font=('Consolas',7),anchor='e' if side<0 else 'w'))
        self.ready,self.last_style = True,None
        self.tick(0,self.state,self.audio,self.mic_active)

    def transform(self,x,y,z,spin=0.):
        c,s = math.cos(spin),math.sin(spin)
        x,z = x*c+z*s,z*c-x*s
        y,z = y*.91-z*.415,y*.415+z*.91
        x,y = x*.966-y*.259,x*.259+y*.966
        depth = 1+z*.12
        return self.cx+x*self.radius*depth,self.cy+y*self.radius*depth,z

    def project(self,x,y,z,spin=0.):
        return self.transform(x,y,z,spin)[:2]

    def tick(self,dt,state,level=0.,mic_active=True):
        self.state,self.mic_active = state,mic_active
        if not self.ready: return
        dt = max(0.,min(.1,dt))
        self.motion.approach(appearance(state,mic_active),dt)
        m = self.motion
        sleeping = state == 'Offline' or (state == 'Idle' and not mic_active)
        self.elapsed += dt*self.intensity*(.6 if sleeping else 1.)
        self.phase += dt*m.speed*self.intensity
        t,p,r = self.elapsed,self.phase,self.radius
        self.audio += (max(0.,min(1.,level))-self.audio)*(1-math.exp(-dt*12))
        beat = voice_envelope(t) if state == 'Speaking' else self.audio if state == 'Listening' else 0.
        self.reaction += (beat-self.reaction)*(1-math.exp(-dt*10))
        breath = math.sin(t*1.8)
        expansion = m.expansion*(1+.025*breath*self.intensity+.10*self.reaction)
        energy = m.brightness*(.91+.09*breath+.10*self.reaction)
        if state in ('Error','Offline'): energy *= .88+.08*math.sin(t*9)+.04*math.sin(t*17)
        hue = AMBER if state == 'Error' else WARM if state == 'Offline' else CYAN
        self.energy = energy
        style = 'error' if state in ('Error','Offline') else 'dim' if sleeping else 'bright' if state in ('Speaking','Listening') else 'normal'
        if self.last_style != (style,state,mic_active):
            self.itemconfigure(self.glow,image=self.blooms[style])
            self.itemconfigure(self.inner_glow,image=self.blooms[style+'-node'])
            captions = {'Idle':'READY WHEN YOU ARE' if mic_active else 'PROJECTION ACTIVE / MICROPHONE OFF',
                        'Listening':'LISTENING TO YOU','Processing':'ANALYZING REQUEST',
                        'Speaking':'VOICE RESONANCE / SPEAKING','Error':'SIGNAL INTERRUPTED','Offline':'PROJECTION OFFLINE'}
            self.itemconfigure(self.caption,text=captions.get(state,'READY'))
            self.itemconfigure(self.signal,text='STANDBY' if sleeping and state=='Idle' else state.upper(),fill=hue)
            self.last_style = (style,state,mic_active)
        floor,roof = self.cy+r*1.13,self.cy-r*1.12
        for i,item in enumerate(self.emitter):
            rr = r*(.32+i*.084)
            self.coords(item,self.cx-rr,floor-rr*.16,self.cx+rr,floor+rr*.16)
            self.itemconfigure(item,outline=mix(hue,energy*(.65-i*.085)))
        for i,item in enumerate(self.cap):
            rr = r*(.25+i*.10)
            self.coords(item,self.cx-rr,roof-rr*.14,self.cx+rr,roof+rr*.14)
            self.itemconfigure(item,outline=mix(hue,energy*(.48-i*.1)))
        for i,item in enumerate(self.beams):
            x = (i-2)*r*.05
            self.coords(item,self.cx+x,floor,self.cx+x*.25,roof)
            self.itemconfigure(item,fill=mix(hue,energy*(.12 if i==2 else .035)))
        for i,item in enumerate(self.ring_arcs):
            rr = r*(1.02+(i%4)*.055)
            self.coords(item,self.cx-rr,self.cy-rr*.91,self.cx+rr,self.cy+rr*.91)
            self.itemconfigure(item,start=math.degrees(p*(1 if i%2 else -.72))+i*37,
                               extent=8+(i%4)*12,outline=mix(hue,energy*(.25+(i%4)*.17)))
        scene = []
        scale = .79*expansion
        for index,(item,points) in enumerate(zip(self.mesh,self.geometry)):
            projected = [self.transform(x*scale,y*scale,z*scale,p*.58) for x,y,z in points]
            z = sum(point[2] for point in projected)/len(projected)
            front = max(0.,min(1.,(z/scale+1)/2))
            self.coords(item,*(value for point in projected for value in point[:2]))
            self.itemconfigure(item,fill=mix(GLOW if front>.55 else hue,energy*(.10+.78*front**1.5)),
                               width=1.2 if front>.7 else 1,
                               dash=(2,4) if state=='Processing' and index%7==0 else ())
            scene.append((z,item))
        # Independently tilted trails pass behind and in front of the spherical shell.
        for orbit in range(3):
            head = p*(.9+orbit*.27)*(-1 if orbit==1 else 1)+orbit*2.1
            tilt = -.55+orbit*.62
            rr = (.95+orbit*.055)*(1+.055*self.reaction)
            for segment in range(12):
                points = []
                for j in range(6):
                    a = head-(segment+j/5)*math.tau/12
                    points.append(self.transform(math.cos(a)*rr,math.sin(a)*rr*math.sin(tilt),
                                                 math.sin(a)*rr*math.cos(tilt),orbit*.55))
                z = sum(point[2] for point in points)/len(points)
                item = self.orbits[orbit*12+segment]
                self.coords(item,*(value for point in points for value in point[:2]))
                strength = (.2+.72*(1-segment/12)**2)*(.48+.52*(z/rr+1)/2)
                self.itemconfigure(item,fill=mix(GLOW,energy*strength),width=2 if segment<2 else 1)
                scene.append((z,item))
            x,y,z = self.transform(math.cos(head)*rr,math.sin(head)*rr*math.sin(tilt),
                                   math.sin(head)*rr*math.cos(tilt),orbit*.55)
            size = max(1.5,r*.012)*(1+.35*self.reaction)
            item = self.orbit_heads[orbit]
            self.coords(item,x-size,y-size,x+size,y+size)
            self.itemconfigure(item,fill=mix(HOT,energy),outline=mix(hue,energy*.65))
            scene.append((z,item))
        for i,item in enumerate(self.nodes):
            y = 1-2*(i+.5)/len(self.nodes)
            a = i*2.399963+p*.35
            rr = (.83+.055*math.sin(t*.8+i))*(1+.10*self.reaction)
            ring = math.sqrt(1-y*y)
            x,yy,z = self.transform(math.cos(a)*ring*rr,y*rr,math.sin(a)*ring*rr,p*.14)
            size = (.55+(i%4)*.24)*(1.05+.45*z)
            self.coords(item,x-size,yy-size,x+size,yy+size)
            self.itemconfigure(item,fill=mix(HOT if i%7==0 else hue,energy*(.26+.68*(z+1)/2)))
            scene.append((z,item))
        scene.append((0,self.inner_glow))
        pulse = 1+.6*self.reaction+.09*breath
        for i,item in enumerate(self.nucleus):
            rr = r*(.11-i*.025)*pulse
            self.coords(item,self.cx-rr,self.cy-rr*1.10,self.cx+rr,self.cy+rr*1.10)
            self.itemconfigure(item,outline=mix(HOT,energy*(.45+i*.18)),
                               fill=mix(hue if i<2 else HOT,energy*(.25+i*.24)))
            scene.append((.001+i*.001,item))
        for i,item in enumerate(self.scans):
            v = -1+2*((p*.32+i/5)%1)
            half = r*scale*math.sqrt(max(0,1-v*v))
            y = self.cy+v*r*scale
            self.coords(item,self.cx-half,y,self.cx+half,y)
            self.itemconfigure(item,fill=mix(hue,energy*(.4 if state=='Processing' else .045)))
            scene.append((.9,item))
        # Painter's order: rear trails -> energy node -> foreground shell.
        for _,item in sorted(scene): self.tag_raise(item)
        for i,item in enumerate(self.resonance):
            cycle = (t*(.63 if state=='Speaking' else .36)+i/4)%1
            points = []
            for j in range(65):
                a = j*math.tau/64
                rr = r*(.22+cycle*.90+.018*math.sin(a*14-t*7)*self.reaction)
                points.extend((self.cx+math.cos(a)*rr,self.cy+math.sin(a)*rr*.86))
            self.coords(item,*points)
            self.itemconfigure(item,fill=mix(hue,energy*m.waves*(1-cycle)*(.1+.55*self.reaction)))
            self.tag_raise(item)
        for item in (*self.annotations,self.caption,self.signal): self.tag_raise(item)
