<script setup>
import {onBeforeUnmount, onMounted, reactive, ref} from "vue";
import {fetchGet} from "@/utilities/fetch.js";
import {useRoute} from "vue-router";
import dayjs from "dayjs";
import LocaleText from "@/components/text/localeText.vue";
import Backup from "@/components/configurationComponents/backupRestoreComponents/backup.vue";

const route = useRoute()
const backups = ref([])
const loading = ref(true)
const emit = defineEmits(["close", "refreshPeersList"])

onMounted(() => {
	loadBackup();
})

const loadBackup = () => {
	loading.value = true
	fetchGet("/api/getWireguardConfigurationBackup", {
		configurationName: route.params.id
	}, (res) => {
		backups.value = res.data;
		loading.value = false;
	})
}

const createBackup = () => {
	fetchGet("/api/createWireguardConfigurationBackup", {
		configurationName: route.params.id
	}, (res) => {
		backups.value = res.data;
		loading.value = false;
	})
}
</script>

<template>
<div class="peerSettingContainer w-100 h-100 position-absolute top-0 start-0 overflow-y-scroll" ref="editConfigurationContainer">
	<div class="d-flex h-100 w-100">
		<div class="modal-dialog-centered dashboardModal w-100 h-100 overflow-x-scroll flex-column gap-3 mx-3">
			<div class="my-5 d-flex gap-3 flex-column position-relative">
				<div class="title">
					<div class="d-flex mb-3">
						<h4 class="mb-0">
							<LocaleText t="Backup & Restore"></LocaleText>
						</h4>
						<button type="button" class="btn-close ms-auto" @click="$emit('close')" aria-label="Close"></button>
					</div>
					<button 
						@click="createBackup()"
						class="btn bg-primary-subtle text-primary-emphasis border-primary-subtle rounded-3 w-100">
						<i class="bi bi-plus-circle-fill me-2"></i>
						<LocaleText t="Create Backup"></LocaleText>
					</button>
				</div>
				<div class="position-relative d-flex flex-column gap-3">
					<TransitionGroup name="list1" >
						<div class="text-center title" 
						     key="spinner"
						     v-if="loading && backups.length === 0">
							<div class="spinner-border"></div>
						</div>
						<div class="card my-0 rounded-3"
						     v-else-if="!loading && backups.length === 0"
						     key="noBackups"
						>
							<div class="card-body text-center text-muted">
								<i class="bi bi-x-circle-fill me-2"></i>
								<LocaleText t="No backup yet, click the button above to create backup."></LocaleText>
							</div>
						</div>
						<Backup
							@refresh="loadBackup()"
							@refreshPeersList="emit('refreshPeersList')"
							:b="b" v-for="b in backups"
							:key="b.filename"
						></Backup>
					</TransitionGroup>
				</div>
			</div>

		</div>
	</div>
</div>
</template>

<style scoped>
.card, .title{
	width: 100%;
}

@media screen and (min-width: 700px) {
	.card, .title{
		width: 700px;
	}
}

.animate__fadeInUp{
	animation-timing-function: cubic-bezier(0.42, 0, 0.22, 1.0)
}

.list1-move, /* apply transition to moving elements */
.list1-enter-active,
.list1-leave-active {
	transition: all 0.5s cubic-bezier(0.42, 0, 0.22, 1.0);
}



.list1-enter-from,
.list1-leave-to {
	opacity: 0;
	transform: translateY(30px);
}

/* ensure leaving items are taken out of layout flow so that moving
   animations can be calculated correctly. */
.list1-leave-active {
	width: 100%;
	position: absolute;
}
</style>