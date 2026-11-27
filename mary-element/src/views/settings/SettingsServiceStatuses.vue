<template>
  <GenericSettingsView
    title="Service User Statuses"
    entityName="Service Status"
    apiEndpoint="/service-statuses"
    :hasCode="true"
    :hasDescription="true"
  />
</template>

<script setup>
import GenericSettingsView from './GenericSettingsView.vue'
</script>
