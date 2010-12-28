import datetime, math
from pymfc import app, wnd, traynotify, gdi, menu, metric, layout
from pymfc import iconbtn, winconst

TIMEOUT = 60*25 # 25 min

def sec_to_str(s):
    h = s//3600
    m = (s-h*3600)//60
    sec = s % 60
    
    return u"%02d:%02d:%02d" % (h, m, sec)

class Pomodoro:
    started = None
    stopped = None
    resumed = None
    paused = None
    elapse = 0
    
    def __init__(self):
        self.started = self.resumed = datetime.datetime.now()
    
    def pause(self):
        if self.paused or self.stopped:
            return
        self.paused = datetime.datetime.now()
        self.elapse += (self.paused - self.resumed).seconds
        self.resumed = None
    
    def resume(self):
        if not self.paused or self.stopped:
            return

        self.paused = None
        self.resumed = datetime.datetime.now()
    
    def getelapse(self):
        if self.paused or self.stopped:
            return self.elapse
        else:
            return self.elapse + (datetime.datetime.now() - self.resumed).seconds
    
    def stop(self):
        self.stopped = datetime.datetime.now()
        if self.resumed:
            self.elapse += (self.stopped - self.resumed).seconds
        self.paused = None

class PomoTimerApp:
    cur = None
    
    def __init__(self):
        self.hist = []
        self.started = datetime.datetime.now()
        
    def run(self):
        self.notifyframe = NotifyFrame()
        self.notifyframe.create()
        
        self.pframe = PFrame()
        self.pframe.create()
        
        app.run()
        
    def start(self):
        self.cur = Pomodoro()
        self.hist.append(self.cur)

class Chart(wnd.Wnd):
    WNDCLASS_BACKGROUNDCOLOR = 0xffffff
    WNDCLASS_CURSOR = gdi.Cursor(arrow=True)
    PEN = gdi.Pen(color=0xf08080, width=1)
    PIEBRUSH = gdi.Brush(color=0x0050ff)
    CHARTBRUSH = gdi.Brush(color=0x905000)
    
    def _prepare(self, kwargs):
        super(Chart, self)._prepare(kwargs)
        self.msgproc.PAINT = self.__onPaint
    
    def __iterPie(self):
        now = datetime.datetime.now()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today+datetime.timedelta(days=1)
        for pomo in pomotimer.hist:
            start, stop = pomo.started, pomo.stopped
            if not stop:
                stop = now
            if stop <= today:
                continue
            if start >= tomorrow:
                continue
            
            start = max(start, today)
            stop = min(stop, tomorrow)
            
            yield (start-today).seconds, (stop-today).seconds
            
#        return [
#            (3600*0, 3600*2),
#            (3600*3, 3600*3.5),
#            (3600*5, 3600*7),
#            (3600*10, 3600*11),
#            (3600*11.5, 3600*12),
#            (3600*13, 3600*15),
#            (3600*17, 3600*19),
#            (3600*23, 3600*24),
#        ]


    def __sec2rad(self, sec):
        return math.pi - math.pi*(float(sec)/(3600*12))

    def __onPaint(self, msg):
        dc = gdi.PaintDC(msg.wnd)

        try:
            l, t, r, b = self.getClientRect()
            w = r-l
            h = b-t
            r = (min(w, h)-5)/2.0

            pdc = dc.createCompatibleDC()
            bmp = dc.createCompatibleBitmap(w, h)
            orgbmp = pdc.selectObject(bmp)

            pdc.fillSolidRect((0, 0, w, h), self.WNDCLASS_BACKGROUNDCOLOR)
            pdc.selectObject(self.PEN)
            pdc.selectObject(self.CHARTBRUSH)

            circle = (w/2-r, h/2-r, w/2+r, h/2+r)
            pdc.ellipse(circle)

            pdc.selectObject(self.PIEBRUSH)
            for f, t in self.__iterPie():
                f = self.__sec2rad(f)
                fpos = int(w/2+math.cos(f)*r), int(h/2-math.sin(f)*r)

                t = self.__sec2rad(t)
                tpos = int(w/2+math.cos(t)*r), int(h/2-math.sin(t)*r)
                
                if fpos != tpos:
                    pdc.pie(circle, tpos, fpos)
                else:
                    pdc.moveTo((w/2, h/2))
                    pdc.lineTo((tpos))

            dc.bitBlt((0, 0, w, h), pdc, (0, 0), srccopy=True)
            pdc.selectObject(orgbmp)
        finally:
            dc.endPaint()
    

class Digit(wnd.Wnd):
    WNDCLASS_BACKGROUNDCOLOR = 0xffffff
    WNDCLASS_CURSOR = gdi.Cursor(arrow=True)
    FONT = gdi.Font(face=u"Arial Black", point=18)
    
    def _prepare(self, kwargs):
        super(Digit, self)._prepare(kwargs)
        
        self._text = u''
        self._color = 0
        self.msgproc.PAINT = self.__onPaint
    
    def __onPaint(self, msg):
        dc = gdi.PaintDC(msg.wnd)
        dc.setTextColor(self._color)
        dc.selectObject(self.FONT)
        try:
            rc = self.getClientRect()
            dc.drawText(self._text, rc, noprefix=True, singleline=True, center=True, vcenter=True)
        finally:
            dc.endPaint()
    
    def setText(self, text):
        if text != self._text:
            self._text = text
            self.invalidateRect(None, erase=True)
    
    def setColor(self, color):
        if color != self._color:
            self._color = color
            self.invalidateRect(None, erase=True)
        
class PFrame(wnd.FrameWnd):
    STYLE = wnd.FrameWnd.STYLE(visible=False, popup=True, overlapped=False, 
        sysmenu=False, caption=False, border=False, thickframe=False, toolwindow=True)
    WNDCLASS_CURSOR = gdi.Cursor(arrow=True)

    CONTEXT=True
    ROLE="frame"
    TITLE = u'PomoTimer'
    WNDCLASS_BACKGROUNDCOLOR = 0xffffff
    
    _notified = False
    
    def _prepare(self, kwargs):
        super(PFrame, self)._prepare(kwargs)
        
        fullscreen = (metric.CXFULLSCREEN, metric.CYFULLSCREEN + metric.CYCAPTION)
        self._size = (300, 200)
        self._pos = (fullscreen[0] - self._size[0]-5, fullscreen[1] - self._size[1]-5)
        
        self._layout = layout.Table(parent=self, pos=(1, 1), margin_right=1, margin_bottom=1,
            extendright=True, extendbottom=True, rowgap=0)

        row = self._layout.addRow(fillvert=True)
        cell = row.addCell()
        self._digits = cell.add(Digit, width=20, extendbottom=True)
        self._digits.ctrl.msgproc.NCHITTEST = self.__onChildNCHitTest
        
        self._chart = cell.add(Chart, extendright=True, extendbottom=True)
        self._chart.ctrl.msgproc.NCHITTEST = self.__onChildNCHitTest
        
        row = self._layout.addRow()
        cell = row.addCell()
        cell.add(None, height=0.5)

        self._buttons = iconbtn.HorzIconButtonBar(parent=self)
        self._btnstart = iconbtn.IconButton(
            title=u'Start', tooltipmsg=u'Start', 
            icon=gdi.Icon(filename=u'start.ico', cx=16, cy=16), 
            bgcolor=None, onclick=self.__onStart)

        self._btnpause = iconbtn.IconButton(
            title=u'Pause', tooltipmsg=u'Pause', 
            icon=gdi.Icon(filename=u'pause.ico', cx=16, cy=16), 
            bgcolor=None, onclick=self.__onPause)

        self._btnstop = iconbtn.IconButton(
            title=u'Stop', tooltipmsg=u'Stop', 
            icon=gdi.Icon(filename=u'stop.ico', cx=16, cy=16), 
            bgcolor=None, onclick=self.__onStop)

        self._btnclose = iconbtn.IconButton(
            title=u'Close', tooltipmsg=u'Close', 
            icon=gdi.Icon(filename=u'close.ico', cx=16, cy=16), 
            bgcolor=None, onclick=self.__onClose)

        self._buttons.setButtons([self._btnstart, self._btnpause, self._btnstop, None, self._btnclose])
        row = self._layout.addRow()
        cell = row.addCell()
        cell.add(self._buttons, height=1.4, extendright=True)
        
        self.msglistener.CREATE = self.__onCreate
        self.msgproc.CLOSE = self.__onClose
        self.msglistener.ACTIVATE = self.__onActivate
        self.msgproc.NCHITTEST = self.__onNCHitTest

    def wndReleased(self):
        super(PFrame, self).wndReleased()
        self._layout = None
        
    def __onCreate(self, msg):
        wnd.TimerProc(1000, self.__onTimer)
    
    def __onClose(self, msg):
        self.showWindow(hide=True)
        
    def __onActivate(self, msg):
        if msg.inactive:
            if self.getHwnd():
                self.showWindow(hide=True)

    def __onChildNCHitTest(self, msg):
        return winconst.HITTEST.HTTRANSPARENT

    def __onNCHitTest(self, msg):
        return winconst.HITTEST.HTCAPTION

    def __onTimer(self):
        if self.getWindowStyle().visible:
            self.__updateDigits()
            self._chart.ctrl.invalidateRect(None, erase=False)

        if not self._notified and pomotimer.cur and not pomotimer.cur.stopped:
            if pomotimer.cur.getelapse() >= TIMEOUT:
                self.setVisible()
                self._notified = True
                
    def __onStart(self, wnd, btn):
        if not pomotimer.cur or pomotimer.cur.stopped:
            pomotimer.start()
            self.__updateDigits()
            self.updatebtn()
            self._notified = False
            
    def __onPause(self, wnd, btn):
        if pomotimer.cur:
            if not pomotimer.cur.paused:
                pomotimer.cur.pause()
            else:
                pomotimer.cur.resume()
            self.__updateDigits()
            self.updatebtn()
    
    def __onStop(self, wnd, btn):
        if pomotimer.cur and not pomotimer.cur.stopped:
            pomotimer.cur.stop()
            self.__updateDigits()
            self.updatebtn()
        
    def __onClose(self, wnd, btn):
        self.showWindow(hide=True)
        
    
    def setVisible(self):
        if self.getHwnd():
            self.__updateDigits()
            self.updatebtn()

            self.enableWindow(False)
            self.showWindow(shownoactivate=True)
            self.setWindowPos(activate=False, placetopmost=True)
            self.enableWindow(True)
            self._setVisible = True

    
    def __updateDigits(self):
        if not pomotimer.cur:
            if not pomotimer.hist:
                digit = sec_to_str((datetime.datetime.now() - pomotimer.started).seconds)
            else:
                digit = sec_to_str((datetime.datetime.now() - pomotimer.hist[-1].stopped).seconds)
        else:
            if pomotimer.cur.stopped:
                digit = sec_to_str((datetime.datetime.now() - pomotimer.cur.stopped).seconds)
            else:
                digit = sec_to_str(pomotimer.cur.getelapse())
        
        self._digits.ctrl.setText(digit)
        
        if not pomotimer.cur or pomotimer.cur.stopped:
            self._digits.ctrl.setColor(0xc0c0c0)
        elif pomotimer.cur.paused:
            self._digits.ctrl.setColor(0x808080)
        else:
            if pomotimer.cur.getelapse() >= TIMEOUT:
                self._digits.ctrl.setColor(0x0050ff)
            else:
                self._digits.ctrl.setColor(0x905000)
        
    def updatebtn(self):
        if not self.getHwnd():
            return

        btnchanged = False
        if not pomotimer.cur or pomotimer.cur.stopped:
            btnchanged |= self._btnstart.setDisabled(False)
            btnchanged |= self._btnpause.setDisabled(True)
            btnchanged |= self._btnpause.pushed(False)
            btnchanged |= self._btnstop.setDisabled(True)
        else:
            btnchanged |= self._btnstart.setDisabled(True)
            btnchanged |= self._btnpause.setDisabled(False)
            if pomotimer.cur.paused:
                btnchanged |= self._btnpause.pushed(True)
            else:
                btnchanged |= self._btnpause.pushed(False)
            btnchanged |= self._btnstop.setDisabled(False)
        
        if btnchanged:
            self._buttons.layout()

class Notify(traynotify.TrayNotify):
    def onRBtnUp(self, msg):
        popup = menu.PopupMenu(u"popup")
        popup.append(menu.MenuItem(u"quit", u"Quit"))
        popup.create()
        msg.wnd.setForegroundWindow()
        pos = msg.wnd.getCursorPos()
        pos =msg.wnd.clientToScreen(pos)
        item = popup.trackPopup(pos, msg.wnd, nonotify=True, returncmd=True)
        if item:
            app.quit(0)

    def onLBtnUp(self, msg):
        pomotimer.pframe.setForegroundWindow()
        pomotimer.pframe.setVisible()
        pomotimer.pframe.setWindowPos(activate=True)
        
    def onMouseMove(self, msg):
        if pomotimer.cur and not pomotimer.cur.stopped:
            s = sec_to_str(pomotimer.cur.getelapse())
            self.setIcon(tip=u"PomoTimer - "+s)
        else:
            self.setIcon(tip=u"PomoTimer")

class NotifyFrame(wnd.FrameWnd):
    STYLE=wnd.FrameWnd.STYLE(visible=False)
    WNDCLASS_CURSOR = gdi.Cursor(arrow=True)
    
    def _prepare(self, kwargs):
        super(NotifyFrame, self)._prepare(kwargs)
        icon = gdi.Icon(filename=u"pomotimer.ico", cx=16, cy=16)
        notify = Notify(self, icon, u"pomotimer")

    def wndReleased(self):
        super(NotifyFrame, self).wndReleased()


def run():
    global pomotimer
    pomotimer = PomoTimerApp()
    pomotimer.run()

if __name__ == '__main__':
    run()

