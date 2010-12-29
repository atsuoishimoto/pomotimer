import datetime, math, os, ConfigParser, StringIO, winsound
from pymfc import app, wnd, traynotify, gdi, menu, metric, layout
from pymfc import iconbtn, winconst, shellapi



APPNAME = u"PomoTimer"
ICON_POMOTIMER = gdi.Icon(filename=u"pomotimer.ico", cx=16, cy=16)
ICON_PAUSE = gdi.Icon(filename=u"pomotimer_pause.ico", cx=16, cy=16)
ICON_RUN = gdi.Icon(filename=u"pomotimer_run.ico", cx=16, cy=16)

CONFIG = """
[CONFIG]
minutes = 25
soundfile =
"""

CONFIGFILEPATH = os.path.join(
    shellapi.shGetSpecialFolderPath(None, shellapi.CSIDL.appdata, create=False),
    u'pomotimer'
    )
CONFIGFILENAME = os.path.join(CONFIGFILEPATH, u'pomotimer.config')

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
        
        self.__readconfig()
        
    def __readconfig(self):
        config = self.__loadconfig()
        self.timeout = config.getint('CONFIG', 'minutes')
        self.soundfile = unicode(config.get('CONFIG', 'soundfile'), 'utf-8').strip()
        
    def __loadconfig(self):
        config = ConfigParser.SafeConfigParser()
        config.readfp(StringIO.StringIO(CONFIG))
        
        if os.path.exists(CONFIGFILENAME):
            try:
                config.read(CONFIGFILENAME)
            except:
                # ignore errors
                pass
        return config
    
    def run(self):
        self.notifyframe = wnd.FrameWnd(style=wnd.FrameWnd.STYLE(visible=False))
        self.notify = Notify(self.notifyframe, ICON_POMOTIMER, APPNAME)
        self.notifyframe.create()
        
        self.pframe = PFrame()
        self.pframe.create()
        
        app.run()
        
    def start(self):
        self.cur = Pomodoro()
        self.hist.append(self.cur)

    def showConfig(self):
        ret = ConfigDialog().doModal()
        if ret:
            self.timeout, self.soundfile = ret
            config = self.__loadconfig()
            config.set('CONFIG', 'minutes', str(self.timeout))
            config.set('CONFIG', 'soundfile', self.soundfile.encode('utf-8'))
            
            if not os.path.exists(CONFIGFILEPATH):
                os.makedirs(CONFIGFILEPATH)
            with open(CONFIGFILENAME, 'w') as f:
                config.write(f)

class ConfigDialog(wnd.Dialog):
    CONTEXT=True
    TITLE = APPNAME

    def _prepare(self, kwargs):
        super(ConfigDialog, self)._prepare(kwargs)
        
        self._layout = layout.Table(parent=self, adjustparent=True,
            pos=(10,5), margin_bottom=5, margin_right=10, rowgap=5)

        row = self._layout.addRow()
        cell = row.addCell()
        cell.add(u"Pomodoro")
        cell.add(None)

        cell = row.addCell()
        cell.add(wnd.NumEdit, title=unicode(pomotimer.timeout), width=10, name="edit")
        cell.add(u" minutes")

        row = self._layout.addRow()
        cell = row.addCell()
        cell.add(u"Sound file")
        cell.add(None)
        
        cell = row.addCell(fillhorz=True)
        cell.add(wnd.Edit, width=40, title=pomotimer.soundfile, name="soundfilename", extendright=True)
        cell.add(None)
        cell.add(wnd.Button, title=u"Browse", name='browse')

        row = self._layout.addRow()
        cell = row.addCell(colspan=2, alignright=True)

        cell.add(wnd.OkButton, title=u"OK", name='ok')
        cell.add(None)
        cell.add(wnd.CancelButton, title=u"Cancel", name='cancel')

        self._layout.ctrls.edit.msglistener.CHANGE = self.__checkNum
        self._layout.ctrls.browse.msglistener.CLICKED = self.__selectfile
        self.setDefaultValue(None)
        
    def __checkNum(self, msg=None):
        text = self._layout.ctrls.edit.getText()
        ret = None
        try:
            ret = int(text)
        except:
            self._layout.ctrls.ok.enableWindow(False)
        else:
            if ret < 1:
                self._layout.ctrls.ok.enableWindow(False)
            else:
                self._layout.ctrls.ok.enableWindow(True)

        return ret

    def __selectfile(self, msg):
        mediadir = os.path.join(
            shellapi.shGetSpecialFolderPath(None, shellapi.CSIDL.windows, create=False),
            u"Media")

        dlg = wnd.FileDialog(
            title=u'Select sound file', initdir=mediadir, 
            filter=((u'wav file', ('*.wav',)),), nochangedir=True, readonly=True, 
            filemustexist=True)
        
        ret = dlg.openDlg()
        if ret:
            self._layout.ctrls.soundfilename.setText(ret[0])
        

    def onOk(self, msg=None):
        num = self.__checkNum()
        filename = self._layout.ctrls.soundfilename.getText().strip()
        
        self.setResultValue((num, filename))
        self.endDialog(self.IDOK)

    def onCancel(self, msg=None):
        self.setResultValue(None)
        self.endDialog(self.IDCANCEL)


class Chart(wnd.Wnd):
    WNDCLASS_BACKGROUNDCOLOR = 0xffffff
    WNDCLASS_CURSOR = gdi.Cursor(arrow=True)

    CHARTBRUSH = gdi.Brush(color=0x905000)
    CHARTPEN = gdi.Pen(color=0xe0e0e0)

    PIEBRUSH = gdi.Brush(color=0x0050ff)
    PIEPEN = gdi.Pen(color=0xf08080, width=0)
    
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
            pdc.selectObject(self.CHARTPEN)
            pdc.selectObject(self.CHARTBRUSH)

            circle = (w/2-r, h/2-r, w/2+r, h/2+r)
            pdc.ellipse(circle)

            pdc.selectObject(self.PIEPEN)
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
    TITLE = APPNAME
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
            if pomotimer.cur.getelapse() >= pomotimer.timeout*60:
                self.setVisible()
                if pomotimer.soundfile:
                    winsound.PlaySound(pomotimer.soundfile, 
                        winsound.SND_FILENAME | winsound.SND_ASYNC)

                self._notified = True

    def __onStart(self, wnd, btn):
        if not pomotimer.cur or pomotimer.cur.stopped:
            pomotimer.start()
            self.__updateDigits()
            self.__updatebtn()
            self._notified = False
            
    def __onPause(self, wnd, btn):
        if pomotimer.cur:
            if not pomotimer.cur.paused:
                pomotimer.cur.pause()
            else:
                pomotimer.cur.resume()
            self.__updateDigits()
            self.__updatebtn()
    
    def __onStop(self, wnd, btn):
        if pomotimer.cur and not pomotimer.cur.stopped:
            pomotimer.cur.stop()
            self.__updateDigits()
            self.__updatebtn()
        
    def __onClose(self, wnd, btn):
        self.showWindow(hide=True)
        
    
    def setVisible(self):
        if self.getHwnd():
            self.__updateDigits()
            self.__updatebtn()

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
            if pomotimer.cur.getelapse() >= pomotimer.timeout*60:
                self._digits.ctrl.setColor(0x0050ff)
            else:
                self._digits.ctrl.setColor(0x905000)
        
    def __updatebtn(self):
        if not self.getHwnd():
            return

        btnchanged = False
        if not pomotimer.cur or pomotimer.cur.stopped:
            btnchanged |= self._btnstart.setDisabled(False)
            btnchanged |= self._btnpause.setDisabled(True)
            btnchanged |= self._btnpause.pushed(False)
            btnchanged |= self._btnstop.setDisabled(True)
            pomotimer.notify.setIcon(icon=ICON_POMOTIMER)
        else:
            btnchanged |= self._btnstart.setDisabled(True)
            btnchanged |= self._btnpause.setDisabled(False)
            if pomotimer.cur.paused:
                btnchanged |= self._btnpause.pushed(True)
                pomotimer.notify.setIcon(icon=ICON_PAUSE)
            else:
                btnchanged |= self._btnpause.pushed(False)
                pomotimer.notify.setIcon(icon=ICON_RUN)
                
            btnchanged |= self._btnstop.setDisabled(False)
        
        if btnchanged:
            self._buttons.layout()

class Notify(traynotify.TrayNotify):
    def onRBtnUp(self, msg):
        popup = menu.PopupMenu(u"popup")
        popup.append(menu.MenuItem(u"config", u"Config"))
        popup.append(menu.MenuItem(u"quit", u"Quit"))
        popup.create()
        
        msg.wnd.setForegroundWindow()
        pos = msg.wnd.getCursorPos()
        pos =msg.wnd.clientToScreen(pos)
        item = popup.trackPopup(pos, msg.wnd, nonotify=True, returncmd=True)
        
        if item:
            if item.menuid == u"quit":
                pomotimer.pframe.destroy()
                pomotimer.notifyframe.destroy()
            elif item.menuid == u"config":
                pomotimer.showConfig()

    def onLBtnUp(self, msg):
        pomotimer.pframe.setForegroundWindow()
        pomotimer.pframe.setVisible()
        pomotimer.pframe.setWindowPos(activate=True)
        
    def onMouseMove(self, msg):
        if pomotimer.cur and not pomotimer.cur.stopped:
            s = sec_to_str(pomotimer.cur.getelapse())
            if pomotimer.cur.paused:
                self.setIcon(tip="Paused - "+s)
            else:
                self.setIcon(tip=APPNAME + " - "+s)
        else:
            self.setIcon(tip=APPNAME)

def run():
    global pomotimer
    pomotimer = PomoTimerApp()
    pomotimer.run()

if __name__ == '__main__':
    run()

