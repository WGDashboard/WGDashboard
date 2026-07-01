<script setup>
import {computed, ref, useTemplateRef} from "vue";
import PeerSettingsDropdown from "@/components/configurationComponents/peerSettingsDropdown.vue";
import {onClickOutside} from "@vueuse/core";

const props = defineProps(['Peer'])
const subMenuOpened = ref(false)
const getLatestHandshake = computed(() => {
	if (props.Peer.latest_handshake.includes(",")){
		return props.Peer.latest_handshake.split(",")[0]
	}
	return props.Peer.latest_handshake;
})

const target = useTemplateRef('target');
onClickOutside(target, event => {
	subMenuOpened.value = false;
});

const emit = defineEmits(['qrcode', 'configurationFile', 'setting', 'jobs', 'refresh', 'share'])
</script>

<template>
<tr>
	<td>
		<small class="d-flex align-items-center gap-2">
			{{Peer.name ? Peer.name : 'Untitled Peer'}}
			<span v-if="Peer.endpoint && Peer.endpoint !== 'N/A'"
			      class="badge rounded-pill d-inline-flex align-items-center gap-1"
			      style="font-size: 0.6rem; background-color: #0d6efd20; color: #0d6efd; border: 1px solid #0d6efd40;">
				<i class="bi bi-arrow-left-right"></i> Site-to-Site
			</span>
		</small>
	</td>
	<td>
		<small>{{Peer.id}}</small>
	</td>
	<td>
		<small>
			{{Peer.allowed_ip}}
		</small>
	</td>
	<td>
		<small class="text-primary">
			{{(Peer.cumu_receive + Peer.total_receive).toFixed(4)}} GB
		</small>
	</td>
	<td>
		<small class="text-success">
			{{(Peer.cumu_sent + Peer.total_sent).toFixed(4)}} GB
		</small>
	</td>
	<td>
		<small class="text-secondary" v-if="Peer.latest_handshake !== 'No Handshake'">
			<i class="bi bi-arrows-angle-contract"></i>
			{{getLatestHandshake}} ago
		</small>
		<small v-else>N/A</small>
	</td>
	<td>
		<a role="button" class="text-body"
		   @click="subMenuOpened = true">
			<h5 class="mb-0"><i class="bi bi-three-dots"></i></h5>
		</a>
		<Transition name="slide-fade">
			<PeerSettingsDropdown
				@qrcode="(file) => emit('qrcode', file)"
				@configurationFile="(file) => emit('configurationFile', file)"
				@setting="emit('setting')"
				@jobs="emit('jobs')"
				@refresh="emit('refresh')"
				@share="emit('share')"
				:Peer="Peer"
				v-if="subMenuOpened"
				ref="target"
			></PeerSettingsDropdown>
		</Transition>
	</td>
</tr>
</template>

<style scoped>
td{
	background-color: transparent;
}
</style>