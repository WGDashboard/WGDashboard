<script setup async>
import './assets/main.css'
import NotificationList from "@/components/Notification/notificationList.vue";
import {clientStore} from "@/stores/clientStore.js";

const store = clientStore()
fetch("/client/api/serverInformation")
	.then(res => res.json())
	.then(res => store.serverInformation = res.data)
</script>

<template>
	<div data-bs-theme="dark" class="text-body bg-body vw-100 vh-100 bg-body-tertiary">
		<div class="d-flex vh-100 vw-100 p-sm-4 overflow-y-scroll">
			<div class="mx-auto my-sm-auto position-relative"
			     id="listContainer"
			     style="width: 700px">
				<Suspense>
					<RouterView v-slot="{ Component }">
						<Transition name="app" type="transition" mode="out-in">
							<Component :is="Component"></Component>
						</Transition>
					</RouterView>
				</Suspense>
			</div>
		</div>
		<NotificationList></NotificationList>
	</div>
</template>

<style scoped>
@media screen and (max-width: 576px) {
	#listContainer{
		border-radius: 0 !important;
	}
}

</style>
