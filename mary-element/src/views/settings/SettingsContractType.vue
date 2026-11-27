<template>
  <GenericSettingsView
    title="Contract Types Classification"
    entityName="Contract Type"
    apiEndpoint="/contract-types"
    :hasCode="true"
    :hasDescription="true"
  />
</template>

<script setup>
import GenericSettingsView from './GenericSettingsView.vue'
</script>
