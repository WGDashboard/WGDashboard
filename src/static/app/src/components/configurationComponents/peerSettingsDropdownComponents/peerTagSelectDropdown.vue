<script setup lang="ts">
import PeerTagBadge from "@/components/configurationComponents/peerTagBadge.vue";
import {reactive, watch} from "vue";

const props = defineProps(['Peer', 'ConfigurationInfo'])
const groups = reactive({...props.ConfigurationInfo.Info.PeerGroups})
import { fetchPost } from "@/utilities/fetch.js"
const emits = defineEmits(['update'])
watch(() => groups, (newVal) => {
	fetchPost("/api/updateWireguardConfigurationInfo", {
		Name: props.ConfigurationInfo.Name,
		Key: "PeerGroups",
		Value: newVal
	}, (res) => {
		if (res.status){
			emits('update', groups)
		}
	})
}, {
	deep: true
})

const togglePeer = (groupId, peerId) => {
	if (groups[groupId].Peers.includes(peerId)){
		groups[groupId].Peers = groups[groupId].Peers.filter(x => x !== peerId)
	}else{
		groups[groupId].Peers.push(peerId)
	}
}
</script>

<template>
	<ul class="dropdown-menu">
		<li v-for="(group, groupId) in groups" >
			<a role="button"
			   @click="togglePeer(groupId, Peer.id)"
			   class="dropdown-item d-flex align-items-center">
				<i class="bi bi-check-circle-fill" v-if="group.Peers.includes(Peer.id)"></i>
				<i class="bi bi-circle" v-else></i>
				<PeerTagBadge
					class="ms-auto"
					:BackgroundColor="group.BackgroundColor" :GroupName="group.GroupName" :Icon="'bi-' + group.Icon"></PeerTagBadge>
			</a>
		</li>
	</ul>
</template>

<style scoped>

</style>