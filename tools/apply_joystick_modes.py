#!/usr/bin/env python3
"""Two real joystick modes, configurable inside Minecraft touch settings."""
from pathlib import Path
import sys
root=Path(sys.argv[1]).resolve()
def edit(path, old, new):
    p=root/path
    s=p.read_text(encoding="utf-8")
    n=s.count(old)
    if n!=1: raise RuntimeError(f"{path}: expected 1 anchor, found {n}: {old[:85]}")
    p.write_text(s.replace(old,new,1),encoding="utf-8")
layout="crates/horizon-client/src/touch/layout.rs"
edit(layout,"    pub sprint_with_joystick: bool,\n","    pub sprint_with_joystick: bool,\n    pub floating_joystick: bool,\n")
edit(layout,"            sprint_with_joystick: false,\n","            sprint_with_joystick: false,\n            floating_joystick: false,\n")
settings="crates/horizon-client/src/settings.rs"
edit(settings,"    TouchSensitivity,\n    TouchButtonScale,","    TouchSensitivity,\n    TouchFloatingJoystick,\n    TouchButtonScale,")
ui="crates/horizon-client/src/options_ui.rs"
edit(ui,'            Opt::TouchSensitivity => "Touch sensitivity",','            Opt::TouchSensitivity => "Скорость сенсорного управления",\n            Opt::TouchFloatingJoystick => "Тип джойстика",')
edit(ui,'            Opt::TouchAnalog => Some(if s.touch.analog_movement { "ON" } else { "OFF" }.into()),','            Opt::TouchAnalog => Some(if s.touch.analog_movement { "ON" } else { "OFF" }.into()),\n            Opt::TouchFloatingJoystick => Some(if s.touch.floating_joystick { "Плавающий" } else { "Статичный" }.into()),')
edit(ui,"            Opt::TouchAnalog => s.touch.analog_movement ^= true,","            Opt::TouchAnalog => s.touch.analog_movement ^= true,\n            Opt::TouchFloatingJoystick => s.touch.floating_joystick ^= true,")
edit(ui,"                    Opt::TouchSensitivity,\n                    Opt::TouchButtonScale,","                    Opt::TouchSensitivity,\n                    Opt::TouchFloatingJoystick,\n                    Opt::TouchButtonScale,")
touch="crates/horizon-client/src/touch.rs"
edit(touch,"            let p = self.placement(control);\n            let size = p.size * h;","""            let mut p = self.placement(control);
            // Only the active floating stick follows its finger. The saved
            // static layout is never mutated and editor positions are stable.
            if control == Control::Move && self.settings.floating_joystick
                && self.editor.is_none()
                && self.settings.mode != Mode::Dpad
            {
                if let Some(anchor) = self.fingers.values().find_map(|(role, _)|
                    if let Role::Move(anchor) = role { Some(*anchor) } else { None })
                {
                    p.center = anchor;
                }
            }
            let size = p.size * h;""")
edit(touch,"""            let control = self.control_at(point);
            let role = match control {""","""            let control = self.control_at(point).or_else(|| {
                // In floating mode, the left-side movement area can start
                // the stick anywhere not occupied by another button.
                (self.settings.floating_joystick
                    && self.settings.mode != Mode::Dpad
                    && point[0] <= 0.42 && point[1] >= 0.35)
                    .then_some(Control::Move)
            });
            let role = match control {""")
edit(touch,"                    Role::Move(self.placement(Control::Move).center)","""                    Role::Move(if self.settings.floating_joystick
                        && self.settings.mode != Mode::Dpad {
                        point
                    } else {
                        self.placement(Control::Move).center
                    })""")
print("In-game Touch options: adjustable touch speed and floating/fixed joystick.")
