//
//  Generated file. Do not edit.
//

// clang-format off

#include "generated_plugin_registrant.h"

#include <ambient_light/ambient_light_plugin_c_api.h>
#include <flutter_webrtc/flutter_web_r_t_c_plugin.h>
#include <screen_capturer/screen_capturer_plugin.h>

void RegisterPlugins(flutter::PluginRegistry* registry) {
  AmbientLightPluginCApiRegisterWithRegistrar(
      registry->GetRegistrarForPlugin("AmbientLightPluginCApi"));
  FlutterWebRTCPluginRegisterWithRegistrar(
      registry->GetRegistrarForPlugin("FlutterWebRTCPlugin"));
  ScreenCapturerPluginRegisterWithRegistrar(
      registry->GetRegistrarForPlugin("ScreenCapturerPlugin"));
}
