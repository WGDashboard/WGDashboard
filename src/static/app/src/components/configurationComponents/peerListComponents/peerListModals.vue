<script setup>
import {defineAsyncComponent} from "vue";
const props = defineProps({
	configurationModals: Object,
	configurationModalSelectedPeer: Object
})
const emits = defineEmits(["refresh"])

const PeerAssignModal = defineAsyncComponent(() => import("@/components/configurationComponents/peerAssignModal.vue"))
const PeerShareLinkModal = defineAsyncComponent(() => import("@/components/configurationComponents/peerShareLinkModal.vue"))
const PeerJobsModal = defineAsyncComponent(() => import("@/components/configurationComponents/peerJobs.vue"))
const PeerQRCodeModal = defineAsyncComponent(() => import("@/components/configurationComponents/peerQRCode.vue"))
const PeerConfigurationFileModal = defineAsyncComponent(() => import("@/components/configurationComponents/peerConfigurationFile.vue"))
const PeerSettingsModal = defineAsyncComponent(() => import("@/components/configurationComponents/peerSettings.vue"))
</script>

<template>
	<TransitionGroup name="zoom">
		<PeerSettingsModal 
			v-if="configurationModals.peerSetting.modalOpen"
			key="PeerSettingsModal"
			:selectedPeer="configurationModalSelectedPeer"
			@refresh="emits('refresh')"
			@close="configurationModals.peerSetting.modalOpen = false">
		</PeerSettingsModal>
		<PeerQRCodeModal
			key="PeerQRCodeModal"
			v-if="configurationModals.peerQRCode.modalOpen"
			:selectedPeer="configurationModalSelectedPeer"
			@close="configurationModals.peerQRCode.modalOpen = false">
		</PeerQRCodeModal>
		<PeerJobsModal
			key="PeerJobsModal"
			@refresh="emits('refresh')"
			v-if="configurationModals.peerScheduleJobs.modalOpen"
			:selectedPeer="configurationModalSelectedPeer"
			@close="configurationModals.peerScheduleJobs.modalOpen = false">
		</PeerJobsModal>
		<PeerShareLinkModal
			key="PeerShareLinkModal"
			v-if="configurationModals.peerShare.modalOpen"
			@close="configurationModals.peerShare.modalOpen = false;"
			:selectedPeer="configurationModalSelectedPeer">
		</PeerShareLinkModal>
		<PeerConfigurationFileModal
			@close="configurationModals.peerConfigurationFile.modalOpen = false"
			v-if="configurationModals.peerConfigurationFile.modalOpen"
			:selectedPeer="configurationModalSelectedPeer"
		></PeerConfigurationFileModal>
		<PeerAssignModal
			:selectedPeer="configurationModalSelectedPeer"
			@close="configurationModals.assignPeer.modalOpen = false"
			v-if="configurationModals.assignPeer.modalOpen"></PeerAssignModal>
	</TransitionGroup>

</template>

<style scoped>

</style>