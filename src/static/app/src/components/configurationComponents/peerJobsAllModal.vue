<script>
import SchedulePeerJob from "@/components/configurationComponents/peerScheduleJobsComponents/schedulePeerJob.vue";
import {WireguardConfigurationsStore} from "@/stores/WireguardConfigurationsStore.js";
import {v4} from "uuid";
import LocaleText from "@/components/text/localeText.vue";

export default {
	name: "peerJobsAllModal",
	setup(){
		const store = WireguardConfigurationsStore();
		return {store}
	},
	components: {LocaleText, SchedulePeerJob},
	props: {
		configurationPeers: Array[Object]
	},
	computed:{
		getAllJobs(){
			return this.configurationPeers.filter(x => x.jobs.length > 0)
		}
	}
}
</script>

<template>
	<div class="peerSettingContainer w-100 h-100 position-absolute top-0 start-0 overflow-y-scroll">
		<div class="container d-flex h-100 w-100">
			<div class="m-auto modal-dialog-centered dashboardModal">
				<div class="card rounded-3 shadow" style="width: 900px">
					<div class="card-header bg-transparent d-flex align-items-center gap-2 border-0 p-4 pb-2">
						<h4 class="mb-0 fw-normal">
							<LocaleText t="All Active Jobs"></LocaleText>
						</h4>
						<button type="button" class="btn-close ms-auto" @click="this.$emit('close')" aria-label="Close"></button>
					</div>
					<div class="card-body px-4 pb-4 pt-2 ">
						<button class="btn bg-primary-subtle border-1 border-primary-subtle text-primary-emphasis rounded-3 shadow mb-2"

						        @click="this.$emit('allLogs')">
							<i class="bi bi-clock me-2"></i>
							<LocaleText t="Logs"></LocaleText>
						</button>
						<div class="accordion" id="peerJobsLogsModalAccordion" v-if="this.getAllJobs.length > 0">
							<div class="accordion-item" v-for="(p, index) in this.getAllJobs" :key="p.id">
								<h2 class="accordion-header">
									<button class="accordion-button collapsed" type="button" data-bs-toggle="collapse"
									        :data-bs-target="'#collapse_' + index">
										<small>
											<strong>
												<span v-if="p.name">
													{{p.name}} &#x2022; 
												</span>
												<samp class="text-muted">{{p.id}}</samp>
											</strong>
										</small>
									</button>
								</h2>
								<div :id="'collapse_' + index" class="accordion-collapse collapse"
								     data-bs-parent="#peerJobsLogsModalAccordion">
									<div class="accordion-body">
										<SchedulePeerJob
											@delete="this.$emit('refresh')"
											@refresh="this.$emit('refresh')"
											:dropdowns="this.store.PeerScheduleJobs.dropdowns"
											:viewOnly="true"
											:key="job.JobID"
											:pjob="job" v-for="job in p.jobs">
										</SchedulePeerJob>
									</div>
								</div>
							</div>
						</div>
						<div class="card shadow-sm"
						     style="height: 153px"
						     v-else>
							<div class="card-body text-muted text-center d-flex">
								<span class="m-auto">
									<LocaleText t="No active job at the moment."></LocaleText>
								</span>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<style scoped>

</style>