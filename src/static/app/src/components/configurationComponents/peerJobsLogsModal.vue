<script>
import dayjs from "dayjs";
import {fetchGet} from "@/utilities/fetch.js";
import LocaleText from "@/components/text/localeText.vue";
export default {
	name: "peerJobsLogsModal",
	components: {LocaleText},
	props: {
		configurationInfo: Object	
	},
	data(){
		return {
			dataLoading: true,
			data: [],
			logFetchTime: undefined,
			showLogID: false,
			showJobID: true,
			showSuccessJob: true,
			showFailedJob: true,
			showLogAmount: 10
		}
	},
	async mounted(){
		await this.fetchLog();
	},
	methods: {
		async fetchLog(){
			this.dataLoading = true;
			await fetchGet(`/api/getPeerScheduleJobLogs/${this.configurationInfo.Name}`, {}, (res) => {
				this.data = res.data;
				this.logFetchTime = dayjs().format("YYYY-MM-DD HH:mm:ss")
				this.dataLoading = false;
			});
		}	
	},
	computed: {
		getLogs(){
			return this.data
				.filter(x => {
					
					return (this.showSuccessJob && 
						["1", "true"].includes(x.Status)) || (this.showFailedJob && 
						["0", "false"].includes(x.Status))
				})
		},
		showLogs(){
			return this.getLogs.slice(0, this.showLogAmount);
		}
	}
}
</script>

<template>
	<div class="peerSettingContainer w-100 h-100 position-absolute top-0 start-0 overflow-y-scroll">
		<div class="container-fluid d-flex h-100 w-100">
			<div class="m-auto mt-0 modal-dialog-centered dashboardModal" style="width: 100%">
				<div class="card rounded-3 shadow w-100" >
					<div class="card-header bg-transparent d-flex align-items-center gap-2 border-0 p-4 pb-0">
						<h4 class="mb-0">
							<LocaleText t="Jobs Logs"></LocaleText>
						</h4>
						<button type="button" class="btn-close ms-auto" @click="this.$emit('close')"></button>
					</div>
					<div class="card-body px-4 pb-4 pt-2">
						<div v-if="!this.dataLoading">
							<p>
								<LocaleText t="Updated at"></LocaleText>
								: {{this.logFetchTime}}</p>
							<div class="mb-2 d-flex gap-3">
								<button @click="this.fetchLog()"
								        class="btn btn-sm rounded-3 shadow-sm
							        text-info-emphasis bg-info-subtle border-1 border-info-subtle me-1">
									<i class="bi bi-arrow-clockwise me-2"></i>
									<LocaleText t="Refresh"></LocaleText>
								</button>
								<div class="d-flex gap-3 align-items-center">
									<span class="text-muted">
										<LocaleText t="Filter"></LocaleText>
									</span>
									<div class="form-check">
										<input class="form-check-input" type="checkbox" v-model="this.showSuccessJob"
										       id="jobLogsShowSuccessCheck">
										<label class="form-check-label" for="jobLogsShowSuccessCheck">
											<span class="badge text-success-emphasis bg-success-subtle">
												<LocaleText t="Success"></LocaleText>
											</span>
										</label>
									</div>
									<div class="form-check">
										<input class="form-check-input" type="checkbox" v-model="this.showFailedJob"
										       id="jobLogsShowFailedCheck">
										<label class="form-check-label" for="jobLogsShowFailedCheck">
											<span class="badge text-danger-emphasis bg-danger-subtle">
												<LocaleText t="Failed"></LocaleText>
											</span>
										</label>
									</div>
								</div>
								<div class="d-flex gap-3 align-items-center ms-auto">
									<span class="text-muted">
										<LocaleText t="Display"></LocaleText>
									</span>
									<div class="form-check">
										<input class="form-check-input" type="checkbox"
										       v-model="showJobID"
										       id="jobLogsShowJobIDCheck">
										<label class="form-check-label" for="jobLogsShowJobIDCheck">
											<LocaleText t="Job ID"></LocaleText>
										</label>
									</div>
									<div class="form-check">
										<input class="form-check-input" type="checkbox"
										       v-model="showLogID"
										       id="jobLogsShowLogIDCheck">
										<label class="form-check-label" for="jobLogsShowLogIDCheck">
											<LocaleText t="Log ID"></LocaleText>
										</label>
									</div>

								</div>
							</div>
							
							<table class="table">
								<thead>
								<tr>
									<th scope="col">
										<LocaleText t="Date"></LocaleText>
									</th>
									<th scope="col" v-if="showLogID">
										<LocaleText t="Log ID"></LocaleText>
									</th>
									<th scope="col" v-if="showJobID">
										<LocaleText t="Job ID"></LocaleText>
									</th>
									<th scope="col">
										<LocaleText t="Status"></LocaleText>
									</th>
									<th scope="col">
										<LocaleText t="Message"></LocaleText>
									</th>
								</tr>
								</thead>
								<tbody>
									<tr v-for="log in this.showLogs" style="font-size: 0.875rem">
										<th scope="row">{{log.LogDate}}</th>
										<td v-if="showLogID"><samp class="text-muted">{{log.LogID}}</samp></td>
										<td v-if="showJobID"><samp class="text-muted">{{log.JobID}}</samp></td>
										<td>
											<span class="badge" :class="[log.Status === '1' ? 'text-success-emphasis bg-success-subtle':'text-danger-emphasis bg-danger-subtle']">
												{{log.Status === "1" ? 'Success': 'Failed'}}
											</span>
										</td>
										<td>{{log.Message}}</td>
									</tr>
								</tbody>
								
							</table>
							<div class="d-flex gap-2">
								<button v-if="this.getLogs.length > this.showLogAmount"
								        @click="this.showLogAmount += 20"
								        class="btn btn-sm rounded-3 shadow-sm
							 text-primary-emphasis bg-primary-subtle border-1 border-primary-subtle">
									<i class="bi bi-chevron-down me-2"></i>
									Show More
								</button>
								<button v-if="this.showLogAmount > 20"
								        @click="this.showLogAmount = 20"
								        class="btn btn-sm rounded-3 shadow-sm
							 text-primary-emphasis bg-primary-subtle border-1 border-primary-subtle">
									<i class="bi bi-chevron-up me-2"></i>
									Collapse
								</button>
							</div>
						</div>
						<div class="d-flex align-items-center flex-column" v-else>
							<div class="spinner-border text-body" role="status">
								<span class="visually-hidden">Loading...</span>
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