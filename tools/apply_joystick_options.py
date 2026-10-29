#!/usr/bin/env python3
"""Persistent floating/static joystick and adjustable touchscreen sensitivity.

Applied after upstream checkout. No new background tasks or per-frame allocations.
"""
from pathlib import Path
import sys
root=Path(sys.argv[1]).resolve()
def patch(name,old,new):
    f=root/name
    s=f.read_text(encoding="utf-8")
    if s.count(old)!=1:
        raise RuntimeError(f"{name}: expected 1 anchor, found {s.count(old)}: {old[:100]!r}")
    f.write_text(s.replace(old,new,1),encoding="utf-8")

layout="crates/horizon-client/src/touch/layout.rs"
patch(layout,"    pub sprint_with_joystick: bool,\n",
      "    pub sprint_with_joystick: bool,\n    /// Movement joystick follows the first finger contact in its activation zone.\n    pub floating_joystick: bool,\n")
patch(layout,"            sprint_with_joystick: false,\n",
      "            sprint_with_joystick: false,\n            floating_joystick: false,\n")
settings="crates/horizon-client/src/settings.rs"
patch(settings,"    TouchMode,\n    TouchAnalog,",
      "    TouchMode,\n    TouchJoystickStyle,\n    TouchAnalog,")
opts="crates/horizon-client/src/options_ui.rs"
patch(opts,'            Opt::TouchMode => "Control scheme",',
      '            Opt::TouchMode => "Control scheme",\n            Opt::TouchJoystickStyle => "Тип джойстика",')
patch(opts,'            Opt::TouchCircleSize => unit(s.touch.circle_size, 16.0, 64.0),',
      '            Opt::TouchJoystickStyle => Kind::Cycle,\n            Opt::TouchCircleSize => unit(s.touch.circle_size, 16.0, 64.0),')
patch(opts,'            Opt::TouchCircleSize => Some(format!("{} px", s.touch.circle_size.round())),',
      '            Opt::TouchJoystickStyle => Some(if s.touch.floating_joystick { "Плавающий" } else { "Статичный" }.into()),\n            Opt::TouchCircleSize => Some(format!("{} px", s.touch.circle_size.round())),')
patch(opts,'            Opt::TouchAnalog => s.touch.analog_movement ^= true,',
      '            Opt::TouchJoystickStyle => s.touch.floating_joystick ^= true,\n            Opt::TouchAnalog => s.touch.analog_movement ^= true,')
patch(opts,'                let mut rows = vec![Row::Big(Opt::TouchMode)];',
      '                let mut rows = vec![Row::Big(Opt::TouchMode), Row::Big(Opt::TouchJoystickStyle)];')
patch(opts,'            Opt::TouchSensitivity => "Touch sensitivity",',
      '            Opt::TouchSensitivity => "Скорость сенсорного экрана",')

touch="crates/horizon-client/src/touch.rs"
patch(touch,
      '            let (x, y) = (p.center[0] * w - size / 2.0, p.center[1] * h - size / 2.0);',
      '''            let mut center = p.center;
            if control == Control::Move && self.settings.floating_joystick
                && self.settings.mode != Mode::Dpad && self.editor.is_none()
            {
                if let Some(anchor) = self.fingers.values().find_map(|(role, _)| {
                    if let Role::Move(anchor) = role { Some(*anchor) } else { None }
                }) {
                    center = anchor;
                }
            }
            let (x, y) = (center[0] * w - size / 2.0, center[1] * h - size / 2.0);''')
patch(touch,
      '                    Role::Move(self.placement(Control::Move).center)',
      '''                    Role::Move(if self.settings.floating_joystick
                        && self.settings.mode != Mode::Dpad
                    { point } else { self.placement(Control::Move).center })''')
# The floating joystick remains touchable in the original movement region.
# During a drag, drawing and movement calculations share the same anchor.
print("Touch settings: floating/static joystick and sensitivity slider; layout persisted.")
