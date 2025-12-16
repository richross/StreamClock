from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.clock import Clock
from kivy.core.window import Window
from datetime import datetime

#Set Window Fullscreen
Window.fullscreen = 'auto'

class ClockScreen(Screen):
    def __init__(self, **kwargs):
        super(ClockScreen, self).__init__(**kwargs)
        
        # Use FloatLayout as base to allow overlay
        root_layout = FloatLayout()
        
        # Create BoxLayout for clock display
        layout = BoxLayout(orientation='vertical')

        #Clock Label
        self.time_label = Label(
            font_size='120sp',
            markup=True
        )

        #Date Label
        self.date_label = Label(
            font_size='30sp'
        )

        #Add Widgets to layout
        layout.add_widget(Label(size_hint=(1, 0.3))) # Spacer
        layout.add_widget(self.time_label)
        layout.add_widget(self.date_label)
        layout.add_widget(Label(size_hint=(1, 0.3))) # Spacer

        # Add clock layout to root
        root_layout.add_widget(layout)
        
        #invisible Exit button (overlaid on top)
        exit_btn = Button(
            text="",
            background_color=(0,0,0,0),
            size_hint=(1, 1),
            pos_hint={'x': 0, 'y': 0}
        )
        exit_btn.bind(on_press=lambda instance: App.get_running_app().stop())
        root_layout.add_widget(exit_btn)

        self.add_widget(root_layout)
        Clock.schedule_interval(self.update_time, 0.5)

    def update_time(self, dt):
        now = datetime.now()
        time_text = now.strftime("[b]%H:%M[/b]:%S")
        date_text = now.strftime("%A, %B %d, %Y")
        self.time_label.text = time_text
        self.date_label.text = date_text

class ClockApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(ClockScreen(name='clock'))
        return sm

if __name__ == '__main__':
    ClockApp().run()