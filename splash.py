from pathlib import Path
import sys
import time
import tkinter as tk
from PIL import Image, ImageDraw, ImageFont, ImageTk

class StartupSplash:
    """3-second high-frame-rate dissolve splash for SM AutoLab."""
    WIDTH = 760
    HEIGHT = 620
    FPS_MS = 8
    def __init__(self):
        self.root = tk.Tk(); self.root.overrideredirect(True); self.root.configure(bg="#FFFFFF"); self.root.attributes("-topmost", True)
        self.canvas = tk.Canvas(self.root,width=self.WIDTH,height=self.HEIGHT,bg="#FFFFFF",highlightthickness=0,bd=0); self.canvas.pack()
        self._load_assets(); self._center(); self._photo=None; self._start=time.perf_counter(); self._running=True
    def _resource_path(self,name):
        base=Path(getattr(sys,"_MEIPASS",Path(__file__).resolve().parent)); return base/"assets"/name
    def _load_assets(self):
        self.bg=Image.new("RGBA",(self.WIDTH,self.HEIGHT),(255,255,255,255))
        self.main_logo=Image.open(self._resource_path("laboratorio_principal.png")).convert("RGBA"); main_side=400
        self.main_logo=self.main_logo.resize((main_side,main_side),Image.Resampling.LANCZOS)
        self.powered_logo=Image.open(self._resource_path("feegow_powered.png")).convert("RGBA")
        secondary_width=180; secondary_height=max(1,round(self.powered_logo.height*secondary_width/self.powered_logo.width))
        self.powered_logo=self.powered_logo.resize((secondary_width,secondary_height),Image.Resampling.LANCZOS)
        self.font_path_candidates=[Path("C:/Windows/Fonts/segoeui.ttf"),Path("C:/Windows/Fonts/SegoeUI.ttf"),Path("C:/Windows/Fonts/arial.ttf")]
        self.font_path=next((p for p in self.font_path_candidates if p.exists()),None)
        self.powered_font=ImageFont.truetype(str(self.font_path),17) if self.font_path else ImageFont.load_default()
        self.main_pos=((self.WIDTH-self.main_logo.width)//2,70); self.powered_pos=(self.WIDTH-self.powered_logo.width-20,self.HEIGHT-self.powered_logo.height-22)
    @staticmethod
    def _smoothstep(x):
        x=max(0.0,min(1.0,x)); return x*x*(3.0-2.0*x)
    def _alpha_for_time(self,t):
        if t<1.00:return self._smoothstep(t/1.00)
        if t<1.82:return 1.0
        if t<3.00:return 1.0-self._smoothstep((t-1.82)/1.18)
        return 0.0
    def _render_frame(self,alpha):
        frame=self.bg.copy(); logo=self.main_logo.copy(); logo.putalpha(logo.getchannel("A").point(lambda a:int(a*alpha))); frame.alpha_composite(logo,dest=self.main_pos)
        powered=Image.new("RGBA",(self.powered_logo.width+16,24),(255,255,255,0)); pdraw=ImageDraw.Draw(powered); text="Powered by"; bbox=pdraw.textbbox((0,0),text,font=self.powered_font); tw=bbox[2]-bbox[0]
        pdraw.text((powered.width-tw-8,2),text,fill=(100,106,112,int(235*alpha)),font=self.powered_font); powered.putalpha(powered.getchannel("A").point(lambda a:int(a*alpha)))
        frame.alpha_composite(powered,dest=(self.powered_pos[0]-2,self.powered_pos[1]-18)); logo2=self.powered_logo.copy(); logo2.putalpha(logo2.getchannel("A").point(lambda a:int(a*alpha))); frame.alpha_composite(logo2,dest=self.powered_pos)
        self._photo=ImageTk.PhotoImage(frame); self.canvas.delete("all"); self.canvas.create_image(self.WIDTH//2,self.HEIGHT//2,image=self._photo,anchor="center")
    def _tick(self):
        if not self._running:return
        elapsed=time.perf_counter()-self._start; self._render_frame(self._alpha_for_time(elapsed))
        if elapsed>=3.0:self._running=False; self.root.after(10,self.close); return
        self.root.after(self.FPS_MS,self._tick)
    def _center(self):
        self.root.update_idletasks(); sw=self.root.winfo_screenwidth(); sh=self.root.winfo_screenheight(); x=max((sw-self.WIDTH)//2,0); y=max((sh-self.HEIGHT)//2,0); self.root.geometry(f"{self.WIDTH}x{self.HEIGHT}+{x}+{y}")
    def close(self):
        try:self.root.destroy()
        except Exception:pass
    def run(self):
        self._render_frame(0.0); self._start=time.perf_counter(); self.root.after(0,self._tick); self.root.mainloop()

def run_splash():
    StartupSplash().run()
