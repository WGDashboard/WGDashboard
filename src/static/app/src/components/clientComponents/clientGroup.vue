<script setup lang="ts">
import {computed, onMounted} from "vue";
import LocaleText from "@/components/text/localeText.vue";
import {useRoute} from "vue-router";

const props = defineProps(['groupName', 'clients', 'searchString'])

const getClients = computed(() => {
	const s = props.searchString.toLowerCase()
	if (!props.searchString){
		return props.clients
	}
	return props.clients.filter(
		x =>
			(x.ClientID && x.ClientID.toLowerCase().includes(s)) || 
			(x.Email && x.Email.toLowerCase().includes(s) || 
				(x.Name && x.Name.toLowerCase().includes(s)))
	)
})
const route = useRoute()
onMounted(() => {
	document.querySelector(".clientList .active")?.scrollIntoView()
})
</script>

<template>
	<div class="card rounded-0 border-0">
		<div class="card-header d-flex align-items-center rounded-0">
			<h6 class="my-2">{{ groupName }}</h6>
			<span class="badge text-bg-primary ms-auto">
				<LocaleText :t="getClients.length + ' Clients'"></LocaleText>
			</span>
		</div>
		<div class="card-body p-0">
			<div class="list-group list-group-flush clientList">
				<RouterLink
					:key="client.ClientID"
					:id="'client_' + client.ClientID"
					active-class="active"
					:to="{ name: 'Client Viewer', params: { id: client.ClientID } }"
					class="list-group-item d-flex flex-column border-bottom list-group-item-action client"
				    v-for="client in getClients" >
					<small class="text-body">
						{{ client.Email }}
					</small>
					<small class="text-muted">
						{{ client.Name ? client.Name : 'No Name'}}
					</small>
				</RouterLink>
			</div>
		</div>
	</div>
</template>

<style scoped>

</style>