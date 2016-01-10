'''
Created on Dec 27, 2015

@author: Adam
'''
import pygame
import json
import os
import __builtin__
from traceback import print_last
from importlib import import_module
from shutil import rmtree
from zipfile import ZipFile
from thread import start_new_thread
from datetime import datetime
from __builtin__ import staticmethod

#state = None
screen = None

def getDictValue(d, k, default=None):
    try: return d[k]
    except KeyError: return default
    
def readFile(path):
    f = open(path, "rU")
    lines = []
    for line in f.readlines():
        lines.append(line.rstrip())
    f.close()
    return lines
    
class Thread(object):
    def __init__(self, method, **data):
        self.eventBindings = {}
        self.pause = False
        self.stop = False
        self.firstRun = True
        self.method = method
        self.pause = getDictValue(data, "startPaused", False)
        self.eventBindings["onStart"] = getDictValue(data, "onStart", None)
        self.eventBindings["onStop"] = getDictValue(data, "onStop", None)
        self.eventBindings["onPause"] = getDictValue(data, "onPause", None)
        self.eventBindings["onResume"] = getDictValue(data, "onResume", None)
        self.eventBindings["onCustom"] = getDictValue(data, "onCustom", None)
        
    @staticmethod
    def __defaultEvtMethod(self, *args):
        return
        
    def execEvent(self, evtKey, *params):
        toExec = getDictValue(self.eventBindings, evtKey, Thread.__defaultEvtMethod)
        if toExec == None: return
        if type(toExec) == list:
            toExec[0](*toExec[1])
        else:
            toExec(*params);
        
    def setPause(self, state="toggle"):
        if type(state) != bool:
            self.pause = not self.pause
        else:
            self.pause = state
        if self.pause: self.execEvent("onPause")
        else: self.execEvent("onResume")
        
    def setStop(self):
        self.stop = True
        self.execEvent("onStop")
        
    def run(self):
        if self.firstRun:
            if self.eventBindings["onStart"] != None:
                self.execEvent("onStart")
            self.firstRun = False
        if not self.pause and not self.stop:
            self.method()
            
class Task(Thread):
    def __init__(self, method, *additionalData):
        super(Thread, self).__init__(method)
        self.returnedData = None
        self.additionalData = additionalData
        
    def run(self):
        self.returnedData = self.method(*self.additionalData)
        self.setStop()
        
    def getReturn(self):
        return self.returnedData
        
    def setPause(self): return
    def execEvent(self, evtKey, *params): return
    
class StagedTask(Task):    
    def __init__(self, method, maxStage=10):
        super(Task, self).__init__(method)
        self.stage = 1
        self.maxStage = maxStage
    
    def run(self):
        self.returnedData = self.method(self.stage)
        self.stage += 1
        if self.stage >= self.maxStage:
            self.setStop()
            
class ParallelTask(Task):
    #Warning: This starts a new thread.
    def run(self):
        start_new_thread(self.method, self.additionalData)
        
    def getReturn(self):
        return None
    
    def setStop(self):
        super(Task, self).setStop()
        print "SetStop was called on a ParallelTask. The thread did not stop."
                
class Controller(object):
    def __init__(self):
        self.threads = []
        self.dataRequests = {}
        
    def requestData(self, fromThread, default=None):
        self.dataRequests[fromThread] = default
        
    def getRequestedData(self, fromThread):
        return self.dataRequests[fromThread]
    
    def addThread(self, thread):
        self.threads.append(thread)
        
    def removeThread(self, thread):
        try:
            if type(thread) == int:
                self.threads.pop(thread)
            else:
                self.threads.remove(thread)
        except:
            print "Thread was not removed!"
            
    def stopAllThreads(self):
        for thread in self.threads:
            thread.setStop()
        
    def run(self):
        for thread in self.threads:
            #try:
            thread.run()
            #except:
            #    print "The thread " + str(thread.method) + " has encountered an error. It will be terminated."
            #    print_last()
            #    thread.setStop()
            if thread in self.dataRequests:
                try:
                    self.dataRequests[thread] = thread.getReturn()
                except:
                    self.dataRequests[thread] = False #getReturn called on Thread, not Task
            if thread.stop:
                self.threads.remove(thread)
        
class GUI(object):    
    def __init__(self):
        global screen
        self.orientation = 0 #0 for portrait, 1 for landscape
        self.timer = None
        self.update_interval = 30
        self.width = 240
        self.height = 320
        pygame.init()
        screen = pygame.display.set_mode((self.width, self.height), pygame.HWACCEL)
        screen.blit(pygame.font.Font(None, 20).render("Loading Python OS 6...", 1, (200, 200, 200)), [5, 5])
        pygame.display.flip()
        __builtin__.screen = screen
        globals()["screen"] = screen
        self.timer = pygame.time.Clock()
        pygame.display.set_caption("PyOS 6")
        
    def orient(self, orientation):
        global screen
        if orientation != self.orientation:
            self.orientation = orientation
            if orientation == 0:
                self.width = 240
                self.height = 320
            if orientation == 1:
                self.width = 320
                self.height = 240
            screen = pygame.display.set_mode((self.width, self.height))
            
    def repaint(self):
        screen.fill(state.getColorPalette().getColor("background"))
        
    def refresh(self):
        pygame.display.flip()
        
    def getScreen(self):
        return screen
    
    @staticmethod
    def getCenteredCoordinates(component, larger):
        return [(larger.width / 2) - (component.width / 2), (larger.height / 2) - (component.height / 2)]
        
    class Font(object):        
        def __init__(self, path="res/RobotoCondensed-Regular.ttf", minSize=10, maxSize=30):
            self.path = path
            curr_size = minSize
            self.sizes = {}
            while curr_size <= maxSize:
                self.sizes[curr_size] = pygame.font.Font(path, curr_size)
                curr_size += 1
            
        def get(self, size=14):
            if size in self.sizes:
                return self.sizes[size]
            return pygame.font.Font(self.path, size)
            
    class Icons(object):
        def __init__(self):
            self.rootPath = "res/icons/"
            self.icons = {
                     "menu": "menu.png",
                     "unknown": "unknown.png",
                     "error": "error.png",
                     "warning": "warning.png",
                     "file": "file.png",
                     "folder": "folder.png",
                     "wifi": "wifi.png",
                     "python": "python.png",
                     "quit": "quit.png"
                     }
        
        def getIcons(self):
            return self.icons
        
        def getRootPath(self):
            return self.rootPath
        
        def getLoadedIcon(self, icon):
            try:
                return pygame.image.load(os.path.join(self.rootPath, self.icons[icon]))
            except:
                if os.path.exists(icon):
                    return pygame.transform.scale(pygame.image.load(icon), (40, 40))
                if os.path.exists(os.path.join("res/icons/", icon)):
                    return pygame.transform.scale(pygame.image.load(os.path.join("res/icons/", icon)), (40, 40))
                return pygame.image.load(os.path.join(self.rootPath, self.icons["unknown"]))
        
        @staticmethod
        def loadFromFile(path):
            f = open(path, "rU")
            icondata = json.load(f)
            toreturn = GUI.Icons()
            for key in dict(icondata).keys():
                toreturn.icons[key] = icondata.get(key)
            f.close()
            return toreturn
    
    class ColorPalette(object):
        def __init__(self):
            self.palette = {
                       "normal": {
                                  "background": (200, 200, 200),
                                  "item": (20, 20, 20),
                                  "accent": (100, 100, 200),
                                  "warning": (250, 160, 45),
                                  "error": (250, 50, 50)
                                  },
                       "dark": {
                                "background": (50, 50, 50),
                                "item": (220, 220, 220),
                                "accent": (50, 50, 150),
                                "warning": (200, 110, 0),
                                "error": (200, 0, 0)
                                },
                       "light": {
                                 "background": (250, 250, 250),
                                 "item": (50, 50, 50),
                                 "accent": (150, 150, 250),
                                 "warning": (250, 210, 95),
                                 "error": (250, 100, 100)
                                 }
                       }
            self.scheme = "normal"
        
        def getPalette(self):
            return self.palette
        
        def getScheme(self):
            return self.scheme
        
        def getColor(self, item):
            return self.palette[self.scheme][item]
        
        def setScheme(self, scheme="normal"):
            self.scheme = scheme
        
        @staticmethod
        def loadFromFile(path):
            f = open(path, "rU")
            colordata = json.load(f)
            toreturn = GUI.ColorPalette()
            for key in dict(colordata).keys():
                toreturn.palette[key] = colordata.get(key)
            f.close()
            return toreturn
        
        @staticmethod
        def HTMLToRGB(colorstring):
            colorstring = colorstring.strip()
            if colorstring[0] == '#': colorstring = colorstring[1:]
            if len(colorstring) != 6:
                raise ValueError, "input #%s is not in #RRGGBB format" % colorstring
            r, g, b = colorstring[:2], colorstring[2:4], colorstring[4:]
            r, g, b = [int(n, 16) for n in (r, g, b)]
            return (r, g, b)
        
        @staticmethod
        def RGBToHTMLColor(rgb_tuple):
            hexcolor = '#%02x%02x%02x' % rgb_tuple
            return hexcolor
        
    class LongClickEvent(object):        
        def __init__(self, mouseDown):
            self.mouseDown = mouseDown
            self.mouseDownTime = datetime.now()
            self.mouseUp = None
            self.mouseUpTime = None
            self.intermediatePoints = []
            self.pos = (-1, -1)
            
        def intermediateUpdate(self, mouseMove):
            if self.mouseUp == None:
                self.intermediatePoints.append(mouseMove.pos)
            
        def end(self, mouseUp):
            self.mouseUp = mouseUp
            self.mouseUpTime = datetime.now()
            self.pos = self.mouseUp.pos
            
        def checkValidLongClick(self, time=250): #Checks timestamps against parameter (in milliseconds)
            delta = self.mouseUpTime - self.mouseDownTime
            return (delta.microseconds / 1000) >= time
        
    class EventQueue(object):
        def __init__(self):
            self.events = []
        
        def check(self):
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    State.exit()
                if event.type == pygame.MOUSEBUTTONDOWN:
                    self.events.append(GUI.LongClickEvent(event))
                if event.type == pygame.MOUSEMOTION and len(self.events) > 0 and isinstance(self.events[len(self.events)-1], GUI.LongClickEvent):
                    self.events[len(self.events)-1].intermediateUpdate(event)
                if event.type == pygame.MOUSEBUTTONUP and len(self.events) > 0 and isinstance(self.events[len(self.events)-1], GUI.LongClickEvent):
                    self.events[len(self.events)-1].end(event)
                    if not self.events[len(self.events)-1].checkValidLongClick():
                        self.events[len(self.events)-1] = self.events[len(self.events)-1].mouseUp
        
        def getLatest(self):
            if len(self.events) == 0: return None
            return self.events.pop()
        
        def getLatestComplete(self):
            if len(self.events) == 0: return None
            p = len(self.events) - 1
            while p >= 0:
                event = self.events[p]
                if isinstance(event, GUI.LongClickEvent):
                    if event.mouseUp != None:
                        return self.events.pop(p)
                else:
                    return self.events.pop(p)
                p -= 1
            
        def clear(self):
            self.events = []
        
    class Component(object):                    
        def __init__(self, position, **data):
            self.position = list(position)[:]
            self.width = -1
            self.height = -1
            self.eventBindings = {}
            self.eventData = {}
            self.surface = None
            self.border = 0
            self.borderColor = (0, 0, 0)
            if "surface" in data:
                self.surface = data["surface"]
                if "width" in data or "height" in data:
                    if "width" in data:
                        self.width = data["width"]
                        self.height = self.surface.get_height()
                    if "height" in data:
                        self.height = data["height"]
                        if self.width == -1:
                            self.width = self.surface.get_width()
                    self.surface = pygame.transform.scale(self.surface, (self.width, self.height))
                else:
                    self.width = self.surface.get_width()
                    self.height = self.surface.get_height()
            else:
                self.width = data["width"]
                self.height = data["height"]
                self.surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            if "onClick" in data: self.eventBindings["onClick"] = data["onClick"]
            if "onLongClick" in data: self.eventBindings["onLongClick"] = data["onLongClick"]
            if "onClickData" in data: self.eventData["onClick"] = data["onClickData"]
            if "onLongClickData" in data: self.eventData["onLongClick"] = data["onLongClickData"]
            if "border" in data: 
                self.border = int(data["border"])
                if "borderColor" in data: self.borderColor = data["borderColor"]
            
        def onClick(self):
            if "onClick" in self.eventBindings: 
                if "onClick" in self.eventData:
                    self.eventBindings["onClick"](*self.eventData["onClick"])
                else:
                    self.eventBindings["onClick"]()
            
        def onLongClick(self):
            if "onLongClick" in self.eventBindings:
                if "onLongClick" in self.eventData:
                    self.eventBindings["onLongClick"](*self.eventData["onLongClick"])
                else:
                    self.eventBindings["onLongClick"]()
            
        def render(self, largerSurface):
            if self.border > 0:
                pygame.draw.rect(self.surface, self.borderColor, [0, 0, self.width, self.height], self.border)
            largerSurface.blit(self.surface, self.position)
            
        def refresh(self):
            self.surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            
        def checkClick(self, mouseEvent, offsetX=0, offsetY=0):
            if mouseEvent.pos[0] - offsetX >= self.position[0] and mouseEvent.pos[0] - offsetX <= self.position[0] + self.width:
                if mouseEvent.pos[1] - offsetY >= self.position[1] and mouseEvent.pos[1] - offsetY <= self.position[1] + self.height:
                    return True
            return False
        
        def setPosition(self, pos):
            self.position = list(pos)[:]
        
    class Container(Component):        
        def __init__(self, position, **data):
            super(GUI.Container, self).__init__(position, **data)
            self.transparent = False
            self.backgroundColor = (0, 0, 0)
            self.childComponents = []
            self.SKIP_CHILD_CHECK = False
            if "transparent" in data: self.transparent = data["transparent"]
            if "color" in data: self.backgroundColor = data["color"]
            else: self.backgroundColor = state.getColorPalette().getColor("background")
            if "children" in data: self.childComponents = data["children"] #WARNING: Will fail if "children" is not only Components.
            
        def addChild(self, component):
            self.childComponents.append(component)
            
        def removeChild(self, component):
            self.childComponents.remove(component)
            
        def clearChildren(self):
            for component in self.childComponents:
                self.removeChild(component)
            
        def getClickedChild(self, mouseEvent, offsetX=0, offsetY=0):
            currChild = len(self.childComponents)
            while currChild > 0:
                currChild -= 1
                child = self.childComponents[currChild]
                if "SKIP_CHILD_CHECK" in child.__dict__:
                    if child.SKIP_CHILD_CHECK:
                        if child.checkClick(mouseEvent, offsetX + self.position[0], offsetY + self.position[1]):
                            return child
                        else:
                            continue
                    else:
                        subCheck = child.getClickedChild(mouseEvent, offsetX + self.position[0], offsetY + self.position[1])
                        if subCheck == None: continue
                        return subCheck
                else:
                    if child.checkClick(mouseEvent, offsetX, offsetY):
                        return child
            if self.checkClick(mouseEvent, offsetX, offsetY):
                return self
            return None
        
        def getChildAt(self, position):
            for child in self.childComponents:
                if child.position == list(position):
                    return child
            return None
        
        def render(self, largerSurface):
            if not self.transparent:
                self.surface.fill(self.backgroundColor)
            else:
                self.surface.fill((0, 0, 0, 0))
            for child in self.childComponents:
                child.render(self.surface)
            super(GUI.Container, self).render(largerSurface)
            
        def refresh(self, children=True):
            super(GUI.Container, self).refresh()
            if children:
                for child in self.childComponents:
                    child.refresh()
                
    class AppContainer(Container):        
        def __init__(self, application):
            super(GUI.AppContainer, self).__init__((0, 0), width=screen.get_width(), height=screen.get_height()-40)
            self.application = application
            self.dialog = None
            self.dialogScreenFreeze = None
            self.dialogComponentsFreeze = []
            
        def setDialog(self, dialog):
            self.dialog = dialog
            self.dialogComponentsFreeze = self.childComponents[:]
            self.childComponents = [self.dialog.baseContainer]
            
        def clearDialog(self):
            self.dialog = None
            self.childComponents = self.dialogComponentsFreeze
            
        def render(self):
            if self.dialog == None:
                super(GUI.AppContainer, self).render(self.surface)
            else:
                self.dialog.baseContainer.render(self.surface)
            screen.blit(self.surface, (0, 0))
            
    class Text(Component):        
        def __init__(self, position, text, color=(0,0,0), size=14, **data):
            self.text = text
            self.size = size
            self.color = color
            self.refresh()
            data["surface"] = self.getRenderedText()
            super(GUI.Text, self).__init__(position, **data)
            
        def getRenderedText(self):
            return state.getFont().get(self.size).render(str(self.text), 1, self.color)
            
        def refresh(self):
            self.surface = self.getRenderedText()
            
        def setText(self, text):
            self.text = str(text)
            self.refresh()
            
    class MultiLineText(Text):
        @staticmethod
        def render_textrect(string, font, rect, text_color, background_color, justification=0):
            final_lines = []
            requested_lines = string.splitlines()
            for requested_line in requested_lines:
                if font.size(requested_line)[0] > rect.width:
                    words = requested_line.split(' ')
                    for word in words:
                        if font.size(word)[0] >= rect.width:
                            print "The word " + word + " is too long to fit in the rect passed."
                    accumulated_line = ""
                    for word in words:
                        test_line = accumulated_line + word + " "
                        if font.size(test_line)[0] < rect.width:
                            accumulated_line = test_line 
                        else: 
                            final_lines.append(accumulated_line) 
                            accumulated_line = word + " " 
                    final_lines.append(accumulated_line)
                else: 
                    final_lines.append(requested_line)         
            surface = pygame.Surface(rect.size, pygame.SRCALPHA) 
            surface.fill(background_color) 
            accumulated_height = 0 
            for line in final_lines: 
                if accumulated_height + font.size(line)[1] >= rect.height:
                    print "Once word-wrapped, the text string was too tall to fit in the rect."
                if line != "":
                    tempsurface = font.render(line, 1, text_color)
                    if justification == 0:
                        surface.blit(tempsurface, (0, accumulated_height))
                    elif justification == 1:
                        surface.blit(tempsurface, ((rect.width - tempsurface.get_width()) / 2, accumulated_height))
                    elif justification == 2:
                        surface.blit(tempsurface, (rect.width - tempsurface.get_width(), accumulated_height))
                    else:
                        print "Invalid justification argument: " + str(justification)
                accumulated_height += font.size(line)[1]
            return surface
        
        def __init__(self, position, text, color=(0,0,0), size=14, justification=0, **data):
            self.justification = justification
            self.color = color
            self.size = size
            super(GUI.Text, self).__init__(position, **data)
            super(GUI.MultiLineText, self).__init__(position, text, color, size, **data)
            if self.width > state.getGUI().width:
                self.width = state.getGUI().width
                
        def getRenderedText(self):
            return GUI.MultiLineText.render_textrect(self.text, state.getFont().get(self.size), pygame.Rect(self.position[0], self.position[1], self.width, self.height),
                                                             self.color, (0, 0, 0, 0), self.justification)
            
        def refresh(self):
            self.surface = self.getRenderedText()
            
    class Image(Container):        
        def __init__(self, position, **data):
            self.path = ""
            self.originalSurface = None
            self.transparent = True
            self.SKIP_CHILD_CHECK = True
            if "path" in data:
                self.path = data["path"]
            else:
                self.path = "surface"
            if "surface" not in data:
                data["surface"] = pygame.image.load(data["path"])
            self.originalSurface = data["surface"]
            super(GUI.Container, self).__init__(position, **data)      
            
        def refresh(self):
            super(GUI.Container, self).refresh()
            self.surface = pygame.transform.scale(self.originalSurface, (self.width, self.height))
            
        def render(self, largerSurface):
            super(GUI.Container, self).render(largerSurface)
            
    class Button(Container):
        def __init__(self, position, text, bgColor=(20,20,20), textColor=(200,200,200), textSize=14, **data):
            self.textComponent = GUI.Text((0, 0), text, textColor, textSize)
            self.paddingAmount = 5
            if "padding" in data: self.paddingAmount = data["padding"]
            if "width" not in data: data["width"] = self.textComponent.width + (2 * self.paddingAmount)
            if "height" not in data: data["height"] = self.textComponent.height + (2 * self.paddingAmount)
            super(GUI.Button, self).__init__(position, **data)
            self.SKIP_CHILD_CHECK = True
            self.textComponent.setPosition(GUI.getCenteredCoordinates(self.textComponent, self))
            self.backgroundColor = bgColor
            self.addChild(self.textComponent)
            
        def render(self, largerSurface):
            super(GUI.Button, self).render(largerSurface)
            
        def getClickedChild(self, mouseEvent, offsetX=0, offsetY=0):
            if self.checkClick(mouseEvent, offsetX, offsetY):
                return self
            return None
        
    class Canvas(Container):
        def __init__(self, position, **data):
            super(GUI.Canvas, self).__init__(position, **data)
            
        def getSurface(self):
            return self.surface
        
    class KeyboardButton(Container):
        def __init__(self, position, symbol, altSymbol, **data):
            if "border" not in data:
                data["border"] = 1
                data["borderColor"] = state.getColorPalette().getColor("item")
            super(GUI.KeyboardButton, self).__init__(position, **data)
            self.SKIP_CHILD_CHECK = True
            self.primaryTextComponent = GUI.Text((0, 0), symbol, state.getColorPalette().getColor("item"), 20)
            self.secondaryTextComponent = GUI.Text((self.width-8, 0), altSymbol, state.getColorPalette().getColor("item"), 10)
            self.primaryTextComponent.setPosition([GUI.getCenteredCoordinates(self.primaryTextComponent, self)[0]-6, self.height-self.primaryTextComponent.height-1])
            self.addChild(self.primaryTextComponent)
            self.addChild(self.secondaryTextComponent)
            
        def getClickedChild(self, mouseEvent, offsetX=0, offsetY=0):
            if self.checkClick(mouseEvent, offsetX, offsetY):
                return self
            return None
        
    class TextEntryField(Container):
        def __init__(self, position, initialText="", **data):
            data["onClick"] = self.parseClick
            if "border" not in data:
                data["border"] = 1
                data["borderColor"] = state.getColorPalette().getColor("accent")
            if "textColor" not in data:
                data["textColor"] = state.getColorPalette().getColor("item")
            if "blink" in data:
                self.blinkInterval = data["blink"]
            else:
                self.blinkInterval = 500
            self.doBlink = False
            self.blinkOn = False
            self.lastBlink = datetime.now()
            self.indicatorPosition = len(initialText)
            self.indicatorPxPosition = 0
            super(GUI.TextEntryField, self).__init__(position, **data)
            self.SKIP_CHILD_CHECK = True
            self.textComponent = GUI.Text((2, 0), initialText, data["textColor"], 14)
            self.textComponent.position[1] = GUI.getCenteredCoordinates(self.textComponent, self)[1]
            self.addChild(self.textComponent)
            
        def parseClick(self):
            if state.getKeyboard() == None:
                state.setKeyboard(GUI.Keyboard(self))
            if state.getKeyboard().textEntryField != self:
                state.getKeyboard().setTextEntryField(self)
            else:
                self.doBlink = True
                mousePos = list(pygame.mouse.get_pos())
                mousePos[0] -= self.position[0]
                currFont = state.getFont().get(14)
                currTextString = ""
                pos = 0
                textWidth = 0
                rendered = None
                while pos < len(self.textComponent.text):
                    currTextString = self.textComponent.text[:pos]
                    rendered = currFont.render(currTextString, 1, (0,0,0))
                    textWidth = rendered.get_width()
                    pos += 1
                    if self.position[0]-4+textWidth <= mousePos[0] <= self.position[0]+4+textWidth:
                        break
                if mousePos[0] > textWidth:
                    self.indicatorPosition = len(self.textComponent.text)
                    self.doBlink = False
                else:
                    self.indicatorPxPosition = textWidth
                    self.indicatorPosition = pos
                    self.doBlink = True
            state.getKeyboard().active = True
            
        def appendChar(self, char):
            self.doBlink = False
            self.textComponent.text = self.textComponent.text[:self.indicatorPosition] + char + self.textComponent.text[self.indicatorPosition:]
            self.textComponent.refresh()
            self.indicatorPosition += 1
            
        def backspace(self):
            if self.indicatorPosition >= 1:
                self.indicatorPosition -= 1
                self.textComponent.text = self.textComponent.text[:self.indicatorPosition] + self.textComponent.text[self.indicatorPosition+1:]
                self.textComponent.refresh()
                
        def delete(self):
            if self.indicatorPosition < len(self.textComponent.text):
                self.textComponent.text = self.textComponent.text[:self.indicatorPosition] + self.textComponent.text[self.indicatorPosition+1:]
                self.textComponent.refresh()
                
        def getText(self):
            return self.textComponent.text
                
        def render(self, largerSurface):
            if not self.transparent:
                self.surface.fill(self.backgroundColor)
            else:
                self.surface.fill((0, 0, 0, 0))
            for child in self.childComponents:
                child.render(self.surface)
            if self.doBlink:
                if ((datetime.now() - self.lastBlink).microseconds / 1000) >= self.blinkInterval:
                    self.lastBlink = datetime.now()
                    self.blinkOn = not self.blinkOn
                if self.blinkOn:
                    pygame.draw.rect(self.surface, self.textComponent.color, [2+self.indicatorPxPosition, 2, 2, self.height-4])
            super(GUI.Container, self).render(largerSurface)
            
        def getClickedChild(self, mouseEvent, offsetX=0, offsetY=0):
            if self.checkClick(mouseEvent, offsetX, offsetY):
                return self
            return None
            
    class PagedContainer(Container):
        def __init__(self, position, **data):
            super(GUI.PagedContainer, self).__init__(position, **data)
            self.pages = data.get("pages", [])
            self.currentPage = 0
            self.pageControls = GUI.Container((0, self.height-20), color=state.getColorPalette().getColor("background"), width=self.width, height=20)
            self.pageLeftButton = GUI.Button((0, 0), " < ", state.getColorPalette().getColor("item"), state.getColorPalette().getColor("accent"),
                                            16, width=40, height=20, onClick=self.pageLeft, onLongClick=self.goToPage)
            self.pageRightButton = GUI.Button((self.width-40, 0), " > ", state.getColorPalette().getColor("item"), state.getColorPalette().getColor("accent"),
                                            16, width=40, height=20, onClick=self.pageRight, onLongClick=self.goToLastPage)
            self.pageIndicatorText = GUI.Text((0, 0), str(self.currentPage + 1)+" of "+str(len(self.pages)), state.getColorPalette().getColor("item"),
                                            16)
            self.pageHolder = GUI.Container((0, 0), color=state.getColorPalette().getColor("background"), width=self.width, height=self.height-20)
            self.pageIndicatorText.position[0] = GUI.getCenteredCoordinates(self.pageIndicatorText, self.pageControls)[0]
            super(GUI.PagedContainer, self).addChild(self.pageHolder)
            self.pageControls.addChild(self.pageLeftButton)
            self.pageControls.addChild(self.pageIndicatorText)
            self.pageControls.addChild(self.pageRightButton)
            super(GUI.PagedContainer, self).addChild(self.pageControls)
            
        def addPage(self, page):
            self.pages.append(page)
            self.pageIndicatorText.text = str(self.currentPage + 1)+" of "+str(len(self.pages))
            self.pageIndicatorText.refresh()
            
        def getPage(self, number):
            return self.pages[number]
            
        def pageLeft(self):
            if self.currentPage >= 1:
                self.goToPage(self.currentPage - 1)
        
        def pageRight(self):
            if self.currentPage < len(self.pages) - 1:
                self.goToPage(self.currentPage + 1)
        
        def goToPage(self, number=0):
            self.currentPage = number
            self.pageHolder.childComponents = []
            self.pageHolder.addChild(self.getPage(self.currentPage))
            self.pageIndicatorText.setText(str(self.currentPage + 1)+" of "+str(len(self.pages)))
            self.pageIndicatorText.refresh()
        
        def goToLastPage(self): self.goToPage(len(self.pages) - 1)
        
        def getLastPage(self):
            return self.pages[len(self.pages) - 1]
        
        def generatePage(self, **data):
            if "width" not in data: data["width"] = self.pageHolder.width
            if "height" not in data: data["height"] = self.pageHolder.height
            data["isPage"] = True
            return GUI.Container((0, 0), **data)
        
        def addChild(self, component):
            if self.pages == []:
                self.addPage(self.generatePage(color=self.backgroundColor, width=self.pageHolder.width, height=self.pageHolder.height))
            self.getLastPage().addChild(component)
            
        def removeChild(self, component):
            self.pages[self.currentPage].removeChild(component)
            childrenCopy = self.self.pages[self.currentPage].childComponents[:]
            for page in self.pages:
                for child in page.childComponents:
                    page.removeChild(child)
            for child in childrenCopy:
                self.addChild(child)
                
        def removePage(self, page):
            if type(page) == int:
                self.pages.pop(page)
            else:
                self.pages.remove(page)
            if self.currentPage >= len(self.pages):
                self.goToPage(self.currentPage - 1)
                
        def clearChildren(self):
            self.pages = []
            self.addPage(self.generatePage(color=self.backgroundColor))
            self.goToPage()
            
    class GriddedPagedContainer(PagedContainer):
        def __init__(self, position, rows=5, columns=4, **data):
            self.padding = 5
            if "padding" in data: self.padding = data["padding"]
            self.rows = rows
            self.columns = columns
            super(GUI.PagedContainer, self).__init__(position, **data)
            self.perRow = (self.height-(2*self.padding)) / rows
            self.perColumn = (self.width-(2*self.padding)) / columns
            super(GUI.GriddedPagedContainer, self).__init__(position, **data)
            
        def isPageFilled(self, number):
            if type(number) == int:
                return len(self.pages[number].childComponents) == (self.rows * self.columns)
            else:
                return len(number.childComponents) == (self.rows * self.columns)
        
        def addChild(self, component):
            if self.pages == [] or self.isPageFilled(self.getLastPage()):
                self.addPage(self.generatePage(color=self.backgroundColor))
            newChildPosition = [self.padding, self.padding]
            if self.getLastPage().childComponents == []:
                component.setPosition(newChildPosition)
                self.getLastPage().addChild(component)
                return
            lastChildPosition = self.getLastPage().childComponents[len(self.getLastPage().childComponents) - 1].position[:]
            print lastChildPosition
            print self.padding + (self.perColumn * self.columns)
            if lastChildPosition[0] < self.padding + (self.perColumn * (self.columns - 1)):
                newChildPosition = [lastChildPosition[0]+self.perColumn, lastChildPosition[1]]
            else:
                newChildPosition = [self.padding, lastChildPosition[1]+self.perRow]
            component.setPosition(newChildPosition)
            self.getLastPage().addChild(component)
            
    class ListPagedContainer(PagedContainer):
        def __init__(self, position, **data):
            self.padding = 1
            self.margin = 2
            if "padding" in data: self.padding = data["padding"]
            if "margin" in data: self.margin = data["margin"]
            super(GUI.ListPagedContainer, self).__init__(position, **data)
            
        def getHeightOfComponents(self):
            height = self.padding
            if self.pages == []: return self.padding
            for component in self.getLastPage().childComponents:
                height += component.height + (2*self.margin)
            return height
            
        def addChild(self, component):
            componentHeight = self.getHeightOfComponents()
            if self.pages == [] or componentHeight + (component.height + 2*self.margin) + (2*self.padding) >= self.pageHolder.height:
                self.addPage(self.generatePage(color=self.backgroundColor))
                componentHeight = self.getHeightOfComponents()
            component.setPosition([self.padding, componentHeight])
            self.getLastPage().addChild(component)
            
    class ButtonRow(Container):
        def __init__(self, position, **data):
            self.padding = 2
            if "padding" in data: self.padding = data["padding"]
            self.margin = 2
            if "margin" in data: self.margin = data["margin"]
            super(GUI.ButtonRow, self).__init__(position, **data)
            
        def getLastComponent(self):
            if len(self.childComponents) > 0:
                return self.childComponents[len(self.childComponents) - 1]
            return None
            
        def addChild(self, component):
            component.height = self.height - (2*self.padding)
            last = self.getLastComponent()
            if last != None:
                component.setPosition([last.position[0]+last.width+self.margin, self.padding])
            else:
                component.setPosition([self.padding, self.padding])
            super(GUI.ButtonRow, self).addChild(component)
            
        def removeChild(self, component):
            super(GUI.ButtonRow, self).removeChild(component)
            childrenCopy = self.childComponents[:]
            self.clearChildren()
            for child in childrenCopy:
                self.addChild(child)
            
            
    class FunctionBar(object):
        def __init__(self):
            self.container = GUI.Container((0, state.getGUI().height-40), background=state.getColorPalette().getColor("background"), width=state.getGUI().width, height=40)
            self.launcherApp = state.getApplicationList().getApp("launcher")
            self.menu_button = GUI.Image((0, 0), surface=state.getIcons().getLoadedIcon("menu"), onClick=self.activateLauncher, onLongClick=Application.fullCloseCurrent, onLongClickData=(True,))
            self.app_title_text = GUI.Text((42, 8), "Python OS 6", state.getColorPalette().getColor("item"), 20, onClick=Application.chainRefreshCurrent)
            self.clock_text = GUI.Text((state.getGUI().width-45, 8), self.formatTime(), state.getColorPalette().getColor("accent"), 20) #Add Onclick Menu
            self.container.addChild(self.menu_button)
            self.container.addChild(self.app_title_text)
            self.container.addChild(self.clock_text)
    
        def formatTime(self):
            time = str(datetime.now())
            if time.startswith("0"): time = time[1:]
            return time[time.find(" ")+1:time.find(":", time.find(":")+1)]
        
        def render(self):
            self.clock_text.text = self.formatTime()
            self.clock_text.refresh()
            self.container.render(screen)
            
        def activateLauncher(self):
            if state.getActiveApplication() != self.launcherApp:
                self.launcherApp.activate()
            else:
                Application.fullCloseCurrent()
            
    class Keyboard(object):
        def __init__(self, textEntryField=None, onEnter="return"):
            self.onEnter = onEnter
            self.shiftUp = False
            self.active = False
            self.textEntryField = textEntryField
            self.baseContainer = None
            baseContainerHeight = 100
            if self.textEntryField.position[1] >= state.getActiveApplication().ui.height - 80:
                baseContainerHeight = 100 + self.textEntryField.height
            self.originalTextEntryFieldPosition = self.textEntryField.position[:]
            self.keyboardContainer = GUI.Container((0, state.getGUI().height-100), width=state.getGUI().width, height=100)
            self.keyWidth = self.keyboardContainer.width / 10
            self.keyHeight = self.keyboardContainer.height / 4
            #self.shift_sym = u"\u21E7" Use pygame.freetype?
            #self.enter_sym = u"\u23CE"
            #self.bkspc_sym = u"\u232B"
            #self.delet_sym = u"\u2326"
            self.shift_sym = "sh"
            self.enter_sym = "->"
            self.bkspc_sym = "<-"
            self.delet_sym = "del"
            self.keys1 = [["q", "w", "e", "r", "t", "y", "u", "i", "o", "p"],
                         ["a", "s", "d", "f", "g", "h", "j", "k", "l", self.enter_sym],
                         [self.shift_sym, "z", "x", "c", "v", "b", "n", "m", ",", "."],
                         ["!", "?", " ", "", "", "", "", "-", "'", self.bkspc_sym]]
            self.keys2 = [["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"],
                         ["@", "#", "$", "%", "^", "&", "*", "(", ")", "_"],
                         ["=", "+", "\\", "/", "<", ">", "|", "[", "]", ":"],
                         [";", "{", "}", "", "", "", "", "-", "\"", self.delet_sym]]
            row = 0
            for symrow in self.keys1:
                sym = 0
                for symbol in symrow:
                    button = None
                    if symbol == "": 
                        sym += 1
                        continue
                    if symbol == " ":
                        button = GUI.KeyboardButton((sym * self.keyWidth, row * self.keyHeight), "", self.keys2[row][sym],
                                                    onClick=self.insertChar, onClickData=(self.keys1[row][sym],), 
                                                    onLongClick=self.insertChar, onLongClickData=(self.keys2[row][sym],),
                                                    width=self.keyWidth*5, height=self.keyHeight)
                    else:
                        if symbol == self.shift_sym or symbol == self.enter_sym or symbol == self.bkspc_sym or symbol == self.delet_sym:
                            button = GUI.KeyboardButton((sym * self.keyWidth, row * self.keyHeight), self.keys1[row][sym], self.keys2[row][sym],
                                                    onClick=self.insertChar, onClickData=(self.keys1[row][sym],), 
                                                    onLongClick=self.insertChar, onLongClickData=(self.keys2[row][sym],),
                                                    width=self.keyWidth, height=self.keyHeight, border=1, borderColor=state.getColorPalette().getColor("accent"))
                        else:
                            button = GUI.KeyboardButton((sym * self.keyWidth, row * self.keyHeight), self.keys1[row][sym], self.keys2[row][sym],
                                                        onClick=self.insertChar, onClickData=(self.keys1[row][sym],), 
                                                        onLongClick=self.insertChar, onLongClickData=(self.keys2[row][sym],),
                                                        width=self.keyWidth, height=self.keyHeight)
                    self.keyboardContainer.addChild(button)
                    sym += 1
                row += 1
            if baseContainerHeight == 100:
                self.baseContainer = self.keyboardContainer
            else:
                self.baseContainer = GUI.Container((0, state.getGUI().height-baseContainerHeight), width=state.getGUI().width, height=100)
                self.keyboardContainer.position[1] = self.textEntryField.height
                self.textEntryField.setPosition([0, 0])
                self.baseContainer.addChild(self.textEntryField)
                self.baseContainer.addChild(self.keyboardContainer)
                
        def setOnEnter(self, value="return"):
            self.onEnter = value
            
        def setTextEntryField(self, field):
            self.textEntryField = field
            self.active = True
            
        def getEnteredText(self):
            return self.textEntryField.getText()
                
        def insertChar(self, char):
            if char == self.shift_sym:
                self.shiftUp = not self.shiftUp
                for button in self.baseContainer.childComponents:
                    if self.shiftUp:
                        button.primaryTextComponent.text = button.primaryTextComponent.text.upper()
                    else:
                        button.primaryTextComponent.text = button.primaryTextComponent.text.lower()
                    button.primaryTextComponent.refresh()
                return
            if char == self.enter_sym:
                if self.onEnter == "newline":
                    pass #Only if is MultiLineTextEntryField
                else:
                    self.active = False
                    self.textEntryField.setPosition(self.originalTextEntryFieldPosition)
                    self.textEntryField = None
                return
            if char == self.bkspc_sym:
                self.textEntryField.backspace()
                return
            if char == self.delet_sym:
                self.textEntryField.delete()
            else:
                if self.shiftUp:
                    self.textEntryField.appendChar(char.upper())
                    self.shiftUp = False
                    for button in self.baseContainer.childComponents:
                        button.primaryTextComponent.text = button.primaryTextComponent.text.lower()
                        button.primaryTextComponent.refresh()
                else:
                    self.textEntryField.appendChar(char)
                    
        def render(self, largerSurface):
            self.baseContainer.render(largerSurface)
            
    class Dialog(object):
        def __init__(self, title, text, actionButtons, onResponseRecorded=None):
            self.application = state.getActiveApplication()
            self.title = title
            self.text = text
            self.response = None
            self.baseContainer = GUI.Container((0, 0), width=state.getGUI().width, height=state.getActiveApplication().ui.height, color=(0, 0, 0, 0.5))
            self.container = GUI.Container((0, 50), width=state.getGUI().width, height=140, color=state.getColorPalette().getColor("background"), border=2, borderColor=state.getColorPalette().getColor("accent"))
            self.buttonList = actionButtons
            self.textComponent = GUI.MultiLineText((2, 2), self.text, state.getColorPalette().getColor("item"), 16, width=self.container.width-4, height=108)
            self.buttonRow = GUI.ButtonRow((2, 108), width=state.getGUI().width, height=30, color=(0, 0, 0, 0))
            for button in self.buttonList:
                self.buttonRow.addChild(button)
            self.container.addChild(self.textComponent)
            self.container.addChild(self.buttonRow)
            self.baseContainer.addChild(self.container)
            self.onResponseRecorded = onResponseRecorded
    
        def display(self):
            state.getFunctionBar().app_title_text.setText(self.title)
            self.application.ui.setDialog(self)
        
        def hide(self):
            state.getFunctionBar().app_title_text.setText(state.getActiveApplication().title)
            self.application.ui.clearDialog()
            self.application.ui.refresh()
            
        def recordResponse(self, response):
            self.response = response
            self.hide()
            if self.onResponseRecorded != None:
                self.onResponseRecorded(self.response)
            
        def getResponse(self):
            return self.response
            
    class OKDialog(Dialog):
        def __init__(self, title, text, onResposeRecorded=None):
            okbtn = GUI.Button((0,0), "OK", state.getColorPalette().getColor("item"), state.getColorPalette().getColor("background"), 18,
                               width=100, onClick=self.recordResponse, onClickData=("OK",))
            super(GUI.OKDialog, self).__init__(title, text, [okbtn], onResposeRecorded)
            
    class ErrorDialog(Dialog):
        def __init__(self, text, onResposeRecorded=None):
            okbtn = GUI.Button((0,0), "Acknowledged", state.getColorPalette().getColor("item"), state.getColorPalette().getColor("background"), 18,
                               width=100, onClick=self.recordResponse, onClickData=("Acknowledged",))
            super(GUI.ErrorDialog, self).__init__("Error", text, [okbtn], onResposeRecorded)
            self.container.backgroundColor = state.getColorPalette().getColor("error")
            
    class WarningDialog(Dialog):
        def __init__(self, text, onResposeRecorded=None):
            okbtn = GUI.Button((0,0), "OK", state.getColorPalette().getColor("item"), state.getColorPalette().getColor("background"), 18,
                               width=100, onClick=self.recordResponse, onClickData=("OK",))
            super(GUI.WarningDialog, self).__init__("Warning", text, [okbtn], onResposeRecorded)
            self.container.backgroundColor = state.getColorPalette().getColor("warning")
            
    class YNDialog(Dialog):
        def __init__(self, title, text, onResponseRecorded=None):
            ybtn = GUI.Button((0,0), "Yes", state.getColorPalette().getColor("item"), state.getColorPalette().getColor("background"), 18,
                               width=50, onClick=self.recordResponse, onClickData=("Yes",))
            nbtn = GUI.Button((0,0), "No", state.getColorPalette().getColor("item"), state.getColorPalette().getColor("background"), 18,
                               width=50, onClick=self.recordResponse, onClickData=("No",))
            super(GUI.YNDialog, self).__init__(title, text, [ybtn, nbtn], onResponseRecorded)
            
    class AskDialog(Dialog):
        def __init__(self, title, text, onResposeRecorded=None):
            okbtn = GUI.Button((0,0), "OK", state.getColorPalette().getColor("item"), state.getColorPalette().getColor("background"), 18,
                               width=50, onClick=self.returnRecordedResponse)
            cancelbtn = GUI.Button((0,0), "Cancel", state.getColorPalette().getColor("item"), state.getColorPalette().getColor("background"), 18,
                               width=50, onClick=self.recordResponse, onClickData=("Cancel",))
            super(GUI.AskDialog, self).__init__(title, text, [okbtn, cancelbtn], onResposeRecorded)
            self.textComponent.height -= 20
            self.textComponent.refresh()
            self.textEntryField = GUI.TextEntryField((0, 90), width=self.container.width, height=20)
            
        def returnRecordedResponse(self):
            super(GUI.AskDialog, self).recordResponse(self.textEntryField.getText())
            
    class CustomContentDialog(Dialog):
        def __init__(self, title, customComponent, actionButtons, onResponseRecorded=None):
            self.application = state.getActiveApplication()
            self.title = title
            self.response = None
            self.baseContainer = GUI.Container((0, 0), width=state.getGUI().width, height=state.getActiveApplication().ui.height, color=(0, 0, 0, 0.5))
            self.container = customComponent
            self.buttonList = actionButtons
            self.buttonRow = GUI.ButtonRow((2, self.container.height-30), width=state.getGUI().width, height=30, color=(0, 0, 0, 0))
            for button in self.buttonList:
                self.buttonRow.addChild(button)
            self.container.addChild(self.buttonRow)
            self.baseContainer.addChild(self.container)
            self.onResponseRecorded = onResponseRecorded
    
         
        
class Application(object):  
    @staticmethod
    def dummy(*args, **kwargs): pass
        
    @staticmethod
    def getListings():
        listingsfile = open("apps/apps.json", "rU")
        app_listings = json.load(listingsfile)
        listingsfile.close()
        return app_listings
    
    @staticmethod
    def chainRefreshCurrent():
        if state.getActiveApplication() != None:
            state.getActiveApplication().chainRefresh()
    
    @staticmethod
    def setActiveApp(app="prev", fromDeactivate=False):
        if state.getActiveApplication() != None and not fromDeactivate:
            state.getActiveApplication().deactivate()
        if app == "prev":
            app = state.getApplicationList().getMostRecentActive()
        state.setActiveApplication(app)
        state.getFunctionBar().app_title_text.setText(state.getActiveApplication().title)
        state.getGUI().repaint()
        state.getApplicationList().pushActiveApp(app)
        
    @staticmethod
    def fullCloseApp(app, replace=True):
        app.deactivate(False, replace)
        
    @staticmethod
    def fullCloseCurrent(replace=True):
        Application.fullCloseApp(state.getActiveApplication(), replace)
    
    @staticmethod
    def removeListing(location):
        alist = Application.getListings()
        try: del alist[location]
        except: print "The application listing for " + location + " could not be removed."
        listingsfile = open("apps/apps.json", "w")
        json.dump(alist, listingsfile)
        listingsfile.close()
        
    @staticmethod
    def install(packageloc):
        package = ZipFile(packageloc, "r")
        package.extract("app.json", "temp/")
        app_listing = open("app.json", "rU")
        app_info = json.load(app_listing)
        app_listing.close()
        app_name = str(app_info.get("name"))
        os.mkdir(os.path.join("apps/", app_name))
        package.extractall(os.path.join("apps/", app_name))
        package.close()
        alist = Application.getListings()
        alist[os.path.join("apps/", app_name)] = app_name
        listingsfile = open("apps/apps.json", "w")
        json.dump(alist, listingsfile)
        listingsfile.close()
        return Application(os.path.join("apps/", app_name))
    
    def __init__(self, location):
        self.parameters = {}
        infofile = open(os.path.join(location, "app.json"), "rU")
        app_data = json.load(infofile)
        self.name = str(app_data.get("name"))
        self.title = str(app_data.get("title"))
        self.version = float(app_data.get("version"))
        self.author = str(app_data.get("author"))
        self.module = import_module("apps." + str(app_data.get("module")), "apps")
        self.module.state = state
        try:
            self.mainMethod = getattr(self.module, str(app_data.get("main"))) 
        except:
            self.mainMethod = Application.dummy
        try: self.parameters = app_data.get("more")
        except: pass
        #check for and load event handlers
        self.evtHandlers = {}
        if "onStart" in self.parameters: 
            self.evtHandlers["onStartReal"] = self.parameters["onStart"]
        self.evtHandlers["onStart"] = [self.onStart, ()]
        if "onStop" in self.parameters: self.evtHandlers["onStop"] = getattr(self.module, self.parameters["onStop"])
        if "onPause" in self.parameters: self.evtHandlers["onPause"] = getattr(self.module, self.parameters["onPause"])
        if "onResume" in self.parameters: self.evtHandlers["onResume"] = getattr(self.module, self.parameters["onResume"])
        if "onCustom" in self.parameters: self.evtHandlers["onCustom"] = getattr(self.module, self.parameters["onCustom"])
        self.thread = Thread(self.mainMethod, **self.evtHandlers)
        self.ui = GUI.AppContainer(self)
        infofile.close()
        self.loadColorScheme()
        self.thread = Thread(self.mainMethod, **self.evtHandlers)
        
    def chainRefresh(self):
        self.ui.refresh()
        
    def onStart(self):
        self.ui = GUI.AppContainer(self)
        self.loadColorScheme()
        if "onStartReal" in self.evtHandlers: getattr(self.module, self.evtHandlers["onStartReal"])(state, self)
        
    def loadColorScheme(self):
        if "colorScheme" in self.parameters: 
            state.getColorPalette().setScheme(self.parameters["colorScheme"])
        else: state.getColorPalette().setScheme()
        self.ui.backgroundColor = state.getColorPalette().getColor("background")
        self.ui.refresh()
        
    def activate(self):
        if state.getActiveApplication() == self: return
        if self.thread in state.getThreadController().threads:
            self.thread.setPause(False)
        else:
            if self.thread.stop:
                self.thread = Thread(self.mainMethod, **self.evtHandlers)
            state.getThreadController().addThread(self.thread)
        Application.setActiveApp(self)
        self.loadColorScheme()
            
    def getIcon(self):
        if "icon" in self.parameters:
            if self.parameters["icon"] == None:
                return False
            return state.getIcons().getLoadedIcon(self.parameters["icon"])
        else:
            return state.getIcons().getLoadedIcon("unknown")
        
    def deactivate(self, pause=True, replaceWithMostRecent=False):
        if "persist" in self.parameters:
            if self.parameters["persist"] == False:
                pause = False
        if pause: self.thread.setPause(True)                    
        else: 
            self.thread.setStop()
        state.getApplicationList().closeApp()
        state.getColorPalette().setScheme()
        if replaceWithMostRecent:
            Application.setActiveApp(state.getApplicationList().getMostRecentActive(), True)
        
    def uninstall(self):
        rmtree(self.location, True)
        Application.removeListing(self.location)
        
class ApplicationList(object):    
    def __init__(self):
        self.applications = {}
        self.activeApplications = []
        applist = Application.getListings()
        for key in dict(applist).keys():
            self.applications[applist.get(key)] = Application(key)
            
    def getApp(self, name):
        if name in self.applications:
            return self.applications[name]
        else:
            return None
        
    def getApplicationList(self):
        return self.applications.values()
        
    def pushActiveApp(self, app):
        if app not in self.activeApplications:
            self.activeApplications.insert(0, app)
        else:
            self.switchLast(app)
        
    def closeApp(self):
        if len(self.activeApplications) > 1:
            return self.activeApplications.pop(0)
    
    def switchLast(self, app):
        self.activeApplications.insert(0, self.activeApplications.pop(self.activeApplications.index(app)))
        
    def getMostRecentActive(self):
        if len(self.activeApplications) > 0:
            return self.activeApplications[0]
    
    def getPreviousActive(self):
        if len(self.activeApplications) > 1:
            return self.activeApplications[1]
                
class State(object):                  
    def __init__(self, activeApp=None, colors=None, icons=None, controller=None, eventQueue=None, functionbar=None, font=None, gui=None, appList=None, keyboard=None):
        self.activeApplication = activeApp
        self.colorPalette = colors
        self.icons = icons
        self.threadController = controller
        self.eventQueue = eventQueue
        self.functionBar = functionbar
        self.font = font
        self.appList = appList
        self.keyboard = keyboard
        if gui == None: self.gui = GUI()
        if colors == None: self.colorPalette = GUI.ColorPalette()
        if icons == None: self.icons = GUI.Icons()
        if controller == None: self.threadController = Controller()
        if eventQueue == None: self.eventQueue = GUI.EventQueue()
        if font == None: self.font = GUI.Font()
        
    def getActiveApplication(self): return self.activeApplication
    def getColorPalette(self): return self.colorPalette
    def getIcons(self): return self.icons
    def getThreadController(self): return self.threadController
    def getEventQueue(self): return self.eventQueue
    def getFont(self): return self.font
    def getGUI(self): return self.gui
    def getApplicationList(self): 
        if self.appList == None: self.appList = ApplicationList()
        return self.appList
    def getFunctionBar(self):
        if self.functionBar == None: self.functionBar = GUI.FunctionBar()
        return self.functionBar
    def getKeyboard(self): return self.keyboard
    
    def setActiveApplication(self, app): self.activeApplication = app
    def setColorPalette(self, colors): self.colorPalette = colors
    def setIcons(self, icons): self.icons = icons
    def setThreadController(self, controller): self.threadController = controller
    def setEventQueue(self, queue): self.eventQueue = queue
    def setFunctionBar(self, bar): self.functionBar = bar
    def setFont(self, font): self.font = font
    def setGUI(self, gui): self.gui = gui
    def setApplicationList(self, appList): self.appList = appList
    def setKeyboard(self, keyboard): self.keyboard = keyboard
    
    @staticmethod
    def getState():
        return state
        
    @staticmethod
    def exit():
        state.getThreadController().stopAllThreads()
        pygame.quit()
        exit()
        
    @staticmethod
    def main():
        while True:
            #Limit FPS
            state.getGUI().timer.tick(state.getGUI().update_interval)
            #Update event queue
            state.getEventQueue().check()
            #Refresh main thread controller
            state.getThreadController().run()
            #Paint UI
            if state.getActiveApplication() != None:
                state.getActiveApplication().ui.render()
            state.getFunctionBar().render()
            if state.getKeyboard() != None and state.getKeyboard().active:
                state.getKeyboard().render(screen)
            state.getGUI().refresh()
            #Check Events
            latestEvent = state.getEventQueue().getLatestComplete()
            if latestEvent != None:
                clickedChild = None
                if state.getKeyboard() != None and state.getKeyboard().active:
                    clickedChild = state.getKeyboard().baseContainer.getClickedChild(latestEvent)
                    if clickedChild == None:
                        clickedChild = state.getActiveApplication().ui.getClickedChild(latestEvent)
                    if clickedChild == None and state.getKeyboard().textEntryField.position == [0, 0] and state.getKeyboard().textEntryField.checkClick(latestEvent):
                        clickedChild = state.getKeyboard().textEntryField
                else:
                    if latestEvent.pos[1] < state.getGUI().height - 40:
                        if state.getActiveApplication() != None:
                            clickedChild = state.getActiveApplication().ui.getClickedChild(latestEvent)
                    else:
                        clickedChild = state.getFunctionBar().container.getClickedChild(latestEvent)
                if clickedChild != None:
                    if isinstance(latestEvent, GUI.LongClickEvent):
                        clickedChild.onLongClick()
                    else:
                        clickedChild.onClick()
            
    @staticmethod
    def state_shell():
        #For debugging purposes only. Do not use in actual code!
        print "Python OS 6 State Shell. Type \"exit\" to quit."
        user_input = raw_input ("S> ")
        while user_input != "exit":
            if not user_input.startswith("state.") and user_input.find("Static") == -1: 
                if user_input.startswith("."):
                    user_input = "state" + user_input
                else:
                    user_input = "state." + user_input
            print eval(user_input, {"state": state, "Static": State})
            user_input = raw_input("S> ")
        State.exit(True)
        
    
if __name__ == "__main__":
    state = State()
    globals()["state"] = state
    __builtin__.state = state
    #TEST
    #State.state_shell()
    state.getApplicationList().getApp("home").activate()
    State.main()