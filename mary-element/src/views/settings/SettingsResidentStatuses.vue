<template>
  <GenericSettingsView
    title="UK Resident & Visa Statuses"
    entityName="Resident Status"
    apiEndpoint="/resident-statuses"
    :hasCode="true"
    :hasDescription="true"
  />
</template>

<script setup>
import GenericSettingsView from './GenericSettingsView.vue'
</script>
