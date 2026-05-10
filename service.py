import xbmc
import urllib.request
import xbmcaddon
import xbmcgui
import threading
import json

# --- Configuration ---
ADDON = xbmcaddon.Addon()

CMD_STRAIGHT = "7E81E01F"
CMD_7CH_STEREO = "7E81FF00"
CMD_SURROUND = "7E81FD02"
CMD_INFO = "7F01609F"
CMD_EXIT = "7A85AA55"
last_file = "none"

title_pause = ADDON.getLocalizedString(32006)
title_caption = ADDON.getLocalizedString(32007)

internet_protocols = ('http://', 'https://', 'rtsp://', 'plugin://', 'pvr://')

def get_set_dsp(YIP, mode, mcast):
    def run():
        if mcast:
            dsp_url = f"http://{YIP}/YamahaExtendedControl/v1/main/getStatus"
        else:
            dsp_url = f"http://{YIP}/YamahaRemoteControl/ctrl"
        try:
            if mcast:
                # Setting a timeout is critical for network services
                with urllib.request.urlopen(dsp_url, timeout=5) as response:
                    # Read and decode bytes to string (UTF-8)
                    html = response.read().decode('utf-8')
                    set_dsp(html, YIP, mode, mcast)
            else:
                post = """<YAMAHA_AV cmd="GET"><Main_Zone><Basic_Status>GetParam</Basic_Status></Main_Zone></YAMAHA_AV>"""
                req = urllib.request.Request(dsp_url, data=post.encode('utf-8'), method='POST')
                req.add_header('Content-Type', 'text/xml; charset=utf-8')
                with urllib.request.urlopen(req) as response:
                    html = response.read().decode('utf-8')
                    set_dsp(html, YIP, mode, mcast)
            
        except Exception as e:
            # Catch timeouts, 404s, or connection refused errors
            xbmc.log(f"YAMAHA-SERVICE: urllib error: {str(e)}", xbmc.LOGERROR)
            set_dsp(None, YIP, mode, mcast)

    thread = threading.Thread(target=run)
    # Daemon threads exit automatically when the main service stops
    thread.daemon = True 
    thread.start()
    
def fmode(mode):
    if mode == 1:
        return "7ch_stereo"
    elif mode == 2:
        return "surr_decoder"
    elif mode == 3:
        return "straight"
    else:
        return "NONE"

def set_dsp(html, YIP, mode, mcast):
    cmode = 0
    cmd = ""
    
    if html:
        #xbmc.log(f"YAMAHA-SERVICE: Return html : {html}", xbmc.LOGINFO)
        if mcast:
            if "sound_program" in html:
                data = json.loads(html)
                sound_prog = data.get("sound_program")
                if sound_prog:
                    if sound_prog == fmode(1):
                        cmode = 1
                    elif sound_prog == fmode(2):
                        cmode = 2
                    elif sound_prog == fmode(3):
                        cmode = 3
        else:
            #not multicast
            if "<Straight>On</Straight>" in html:
                cmode = 3
            elif "<Sound_Program>Surround Decoder</Sound_Program>" in html:
                cmode = 2
            elif "<Sound_Program>7ch Stereo</Sound_Program>" in html:
                cmode = 1
                    
    if cmode >=1 and cmode <=3:
        xbmc.log(f"YAMAHA-SERVICE: Yamaha Contacted - Multicast:{mcast} - Current DSP mode : {fmode(cmode)}", xbmc.LOGINFO)
    else:
        xbmc.log(f"YAMAHA-SERVICE: Unable to fetch current DSP mode from Yamaha.", xbmc.LOGERROR)
    
    if mode >= 1 and mode <= 3 and not cmode == mode:
        xbmc.log(f"YAMAHA-SERVICE: Multicast: {mcast} - Setting DSP mode: {fmode(mode)}", xbmc.LOGINFO)
        if mcast:
            if mode == 1 :
                cmd = CMD_7CH_STEREO                    
            elif mode == 2 :
                cmd = CMD_SURROUND                    
            else:
                cmd = CMD_STRAIGHT                    

            send_yamaha_command(cmd,YIP)
        else:
            send_yamaha_oldschool(mode,YIP)
    elif mode >=1 and mode <=3:
        xbmc.log(f"YAMAHA-SERVICE: DSP already where we want - Leaving alone.", xbmc.LOGINFO)
        
def send_yamaha_command(code,ip):
    url = f"http://{ip}/YamahaExtendedControl/v1/system/sendIrCode?code={code}"
    try:
        with urllib.request.urlopen(url, timeout=2) as r:
            pass
    except Exception as e:
        xbmc.log(f"YAMAHA-SERVICE: {ip} Error: {e}", xbmc.LOGERROR)

def send_yamaha_oldschool(mode,ip):
    URL = f"http://{ip}/YamahaRemoteControl/ctrl"
    
    if mode == 1:
        DSP = """<YAMAHA_AV cmd="PUT"><Main_Zone><Surround><Program_Sel><Current><Sound_Program>7ch Stereo</Sound_Program></Current></Program_Sel></Surround></Main_Zone></YAMAHA_AV>"""
    elif mode == 2:
        DSP = """<YAMAHA_AV cmd="PUT"><Main_Zone><Surround><Program_Sel><Current><Sound_Program>Surround Decoder</Sound_Program></Current></Program_Sel></Surround></Main_Zone></YAMAHA_AV>"""
    else:
        DSP = """<YAMAHA_AV cmd="PUT"><Main_Zone><Surround><Program_Sel><Current><Straight>On</Straight></Current></Program_Sel></Surround></Main_Zone></YAMAHA_AV>"""
    
    try:
        req = urllib.request.Request(URL, data=DSP.encode('utf-8'), method='POST')
        req.add_header('Content-Type', 'text/xml; charset=utf-8')
        
        with urllib.request.urlopen(req) as response:
            pass
    except Exception as e:
        xbmc.log(f"YAMAHA-SERVICE: {ip} Error: {e}", xbmc.LOGERROR)

class YamahaService(xbmc.Player):
    def __init__(self):
        super().__init__()
        self.monitor = xbmc.Monitor()

    def pausewhilestopped(self, seconds):
        for _ in range(seconds * 10): # 100ms increments
            if self.monitor.abortRequested():
                return False
            if self.isPlaying(): # If a new video started during the wait
                return False
            xbmc.sleep(100)
        return True

    def pausewhileplay(self, seconds):
        for _ in range(seconds * 10): # 100ms increments
            if self.monitor.abortRequested():
                return False
            if not self.isPlaying(): # If a new video started during the wait
                return False
            xbmc.sleep(100)
        return True


    def _cleanup_receiver(self, event_type):
        global last_file

        theend = int(ADDON.getSetting("dsp_mode"))
        if theend > 0:
            last_file = "none"
        
            self.pausewhilestopped(10)
        
            if not self.isPlaying():
                YIP = ADDON.getSetting('yamaha_ip')
                got_multicast = ADDON.getSettingBool('got_multicast')
                
                try:
                    if got_multicast:
                        if theend == 1:
                            code = CMD_7CH_STEREO
                        elif thecode == 2:
                            code = CMD_SURROUND                        
                        else:
                            code = CMD_STRAIGHT

                        send_yamaha_command(code,YIP)
                        xbmc.log(f"YAMAHA-SERVICE: {event_type} : Multicast - Set Return Mode : {str(theend)}", xbmc.LOGINFO)
                    else:
                        send_yamaha_oldschool(theend,YIP)
                        xbmc.log(f"YAMAHA-SERVICE: {event_type} : YNC - Set Return Mode : {str(theend)}", xbmc.LOGINFO)
                except Exception as e:
                    xbmc.log(f"YAMAHA-SERVICE: ERROR: {e}", xbmc.LOGERROR)
    
    def onPlayBackStopped(self):
        self._cleanup_receiver("STOPPED")
        
    def onPlayBackEnded(self):
        self._cleanup_receiver("ENDED")
            
    def onAVStarted(self):
        global last_file
        
        paused = False
        YIP = ADDON.getSetting('yamaha_ip')
        got_multicast = ADDON.getSettingBool('got_multicast')
        SHOW_ONSCREEN = (ADDON.getSettingBool('show_onscreen') and got_multicast)
        PAUSE = int(ADDON.getSetting('video_pause') or 0)
        ONSCREEN = int(ADDON.getSetting('screen_seconds') or 0)
        SKIPFPS = ADDON.getSettingBool('pause_skip')

        #xbmc.log(f"YAMAHA-SERVICE: {YIP} : ShowScreen: {SHOW_ONSCREEN} Wait: {PAUSE} Show: {ONSCREEN}", xbmc.LOGINFO)
        xbmc.log("YAMAHA-SERVICE: Playback started, fetching audio channel info", xbmc.LOGINFO)
        
        channels = ""
        retries = 0
        fps = 0.0
        
        max_retries = 60 # Wait up to 15 seconds for spin-up
        
        while not channels and retries < max_retries:
            # Check for abort so we don't hang if the user stops the movie while spinning up
            if xbmc.Monitor().abortRequested():
                return
            
            #xbmc.sleep(250) # Wait 1 second before checking again
            if self.isPlayingVideo():    
                channels = xbmc.getInfoLabel('VideoPlayer.AudioChannels')
                
                if SKIPFPS:
                    fps = xbmc.getInfoLabel('Player.Process(VideoFPS)')
                    fps = round(float(fps), 2)
                    xbmc.log(f"YAMAHA-SERVICE: Video FPS:{str(fps)}", xbmc.LOGINFO)
            else:
                channels = 2
                
            if not channels:
                retries += 1
                xbmc.sleep(250) # Wait 1 second before checking again
        
        if channels:
            xbmc.log(f"YAMAHA-SERVICE: {channels} audio channels found : {retries} retries", xbmc.LOGINFO)
            curr_file = self.getPlayingFile()   #xbmc.getInfoLabel('Player.Filename')
            
            #xbmc.log(f"YAMAHA-SERVICE: Contacting Yamaha - # of channels changed or source changed.", xbmc.LOGINFO)
            if int(channels) <= 2:
                if got_multicast :
                    if self.isPlayingVideo():
                        get_set_dsp(YIP, 2, got_multicast)
                    else:
                        get_set_dsp(YIP, 1, got_multicast)
                else :
                    if self.isPlayingVideo():
                        get_set_dsp(YIP, 2, got_multicast)
                    else:
                        get_set_dsp(YIP, 1, got_multicast)
            else:
                if got_multicast :
                    get_set_dsp(YIP, 3, got_multicast)
                else :
                    get_set_dsp(YIP, 3, got_multicast)
        
            xbmc.log(f"YAMAHA-SERVICE: Path/File - {curr_file}", xbmc.LOGINFO)
            if self.isPlayingVideo() and curr_file != last_file :
                if not SKIPFPS or fps not in [29.97, 30.0, 60.0]:
                    if PAUSE > 0 and not curr_file.lower().startswith(internet_protocols):
                        xbmc.log(f"YAMAHA-SERVICE: Pausing for {PAUSE} seconds", xbmc.LOGINFO)
                        self.pause()
                        secs = self.getTime()
                        if secs < 60 : self.seekTime(0.0)
                        paused = True
                        xbmcgui.Dialog().notification(title_pause,title_caption, xbmcgui.NOTIFICATION_INFO, PAUSE*1000)
                        self.pausewhileplay(PAUSE)
                    else:
                        xbmc.log(f"YAMAHA-SERVICE: Skipping pause - No Pause set or Internet Stream", xbmc.LOGINFO)
                else:
                    xbmc.log(f"YAMAHA-SERVICE: Skipping pause - FPS:{str(fps)} doesn't require it.", xbmc.LOGINFO)
                    
                if self.isPlaying():
                    if paused and xbmc.getCondVisibility("Player.Paused"): 
                        self.pause()
                        xbmc.log(f"YAMAHA-SERVICE: Play resumed", xbmc.LOGINFO)
                    if SHOW_ONSCREEN and ONSCREEN>0:
                        xbmc.log(f"YAMAHA-SERVICE: Showing Yamaha AV Info Screen for {ONSCREEN} seconds", xbmc.LOGINFO)
                        send_yamaha_command(CMD_INFO,YIP)
                        self.pausewhileplay(ONSCREEN)
                        send_yamaha_command(CMD_EXIT,YIP)
            else:
                xbmc.log("YAMAHA-SERVICE: Skipping pause and on-screen - Not video or repeat video", xbmc.LOGINFO)
            last_file = curr_file
#            except:
#                pass
        else:
            xbmc.log("YAMAHA-SERVICE: Timeout waiting for drive spin-up.", xbmc.LOGERROR)


# Keep the service alive
if __name__ == '__main__':
    monitor = xbmc.Monitor()
    player_monitor = YamahaService()
    
    xbmc.log("YAMAHA-SERVICE: Background service started", xbmc.LOGINFO)
    
    while not monitor.abortRequested():
        if monitor.waitForAbort(10):
            break

    xbmc.log("YAMAHA-SERVICE: Background service stopping", xbmc.LOGINFO)