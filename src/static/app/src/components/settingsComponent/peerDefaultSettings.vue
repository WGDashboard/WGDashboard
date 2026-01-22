<script setup lang="ts">

import LocaleText from "@/components/text/localeText.vue";
import PeersDefaultSettingsInput from "@/components/settingsComponent/peersDefaultSettingsInput.vue";
</script>

<template>
	<div class="d-flex gap-3 flex-column">
		<div class="card rounded-3">
			<div class="card-header">
				<h6 class="my-2">
					<LocaleText t="Peer Default Settings"></LocaleText>
				</h6>
			</div>
			<div class="card-body">
				<div>
					<PeersDefaultSettingsInput
						targetData="peer_global_dns" title="DNS"></PeersDefaultSettingsInput>
					<PeersDefaultSettingsInput
						targetData="peer_endpoint_allowed_ip" title="Endpoint Allowed IPs"></PeersDefaultSettingsInput>
					<PeersDefaultSettingsInput
						targetData="peer_mtu" title="MTU"></PeersDefaultSettingsInput>
					<PeersDefaultSettingsInput
						targetData="peer_keep_alive" title="Persistent Keepalive"></PeersDefaultSettingsInput>
					<PeersDefaultSettingsInput
						targetData="peer_preshared_key_default" title="Pre-Shared Key Default"></PeersDefaultSettingsInput>
					<PeersDefaultSettingsInput
						targetData="remote_endpoint" title="Peer Remote Endpoint"
						:warning="true" warningText="This will be changed globally, and will be apply to all peer's QR code and configuration file."
					></PeersDefaultSettingsInput>
				</div>
			</div>
		</div>
	</div>
</template>

<style scoped>

</style>
