//
//  Generated file. Do not edit.
//

// clang-format off

#include "generated_plugin_registrant.h"

#include <ambient_light/ambient_light_plugin.h>
#include <flutter_webrtc/flutter_web_r_t_c_plugin.h>
#include <screen_capturer/screen_capturer_plugin.h>

void fl_register_plugins(FlPluginRegistry* registry) {
  g_autoptr(FlPluginRegistrar) ambient_light_registrar =
      fl_plugin_registry_get_registrar_for_plugin(registry, "AmbientLightPlugin");
  ambient_light_plugin_register_with_registrar(ambient_light_registrar);
  g_autoptr(FlPluginRegistrar) flutter_webrtc_registrar =
      fl_plugin_registry_get_registrar_for_plugin(registry, "FlutterWebRTCPlugin");
  flutter_web_r_t_c_plugin_register_with_registrar(flutter_webrtc_registrar);
  g_autoptr(FlPluginRegistrar) screen_capturer_registrar =
      fl_plugin_registry_get_registrar_for_plugin(registry, "ScreenCapturerPlugin");
  screen_capturer_plugin_register_with_registrar(screen_capturer_registrar);
}
