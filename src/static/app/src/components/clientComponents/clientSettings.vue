<script setup lang="ts">
import { ref, reactive } from "vue"
import LocaleText from "@/components/text/localeText.vue";
import OidcSettings from "@/components/clientComponents/clientSettingComponents/oidcSettings.vue";
const emits = defineEmits(['close'])
import { DashboardConfigurationStore } from "@/stores/DashboardConfigurationStore"
const dashboardConfigurationStore = DashboardConfigurationStore()
const loading = ref(false)
const values = reactive({
	allow_local_sign_up: dashboardConfigurationStore.Configuration.Clients.allow_local_sign_up
})
</script>

<template>
<div class="position-absolute w-100 h-100 top-0 start-0 z-1 rounded-3 d-flex p-2" style="background-color: #00000070; z-index: 9999">
	<div class="card m-auto rounded-3" style="width: 700px">
		<div class="card-header bg-transparent d-flex align-items-center gap-2 border-0 p-4 pb-2">
			<h4 class="mb-0">
				<LocaleText t="Clients Settings"></LocaleText>
			</h4>
			<button type="button" class="btn-close ms-auto" @click="emits('close')"></button>
		</div>
		<div class="card-body px-4">
			<div class="py-2">
				<OidcSettings mode="Client"></OidcSettings>
<!--				<hr>-->
<!--				<div>-->
<!--					<div class="d-flex">-->
<!--						<h6 class="mb-0">-->
<!--							<LocaleText t="Allow Local Accounts Sign Up"></LocaleText>-->
<!--						</h6>-->
<!--						<div class="form-check form-switch ms-auto">-->
<!--							<label class="form-check-label" for="allow_local_sign_up">-->
<!--								<LocaleText :t="values.allow_local_sign_up ? 'Enabled':'Disabled'"></LocaleText>-->
<!--							</label>-->
<!--							<input-->
<!--								:disabled="loading"-->
<!--								v-model="values.allow_local_sign_up"-->
<!--								class="form-check-input" type="checkbox" role="switch" id="allow_local_sign_up">-->
<!--						</div>-->
<!--					</div>-->
<!--				</div>-->
			</div>
		</div>
	</div>
</div>
</template>

<style scoped>

</style>