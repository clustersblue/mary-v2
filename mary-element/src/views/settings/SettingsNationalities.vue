<template>
  <GenericSettingsView
    title="Nationalities Master Registry"
    entityName="Nationality"
    apiEndpoint="/nationalities"
    :hasCode="true"
    :hasDescription="true"
  />
</template>

<script setup>
import GenericSettingsView from './GenericSettingsView.vue'
</script>
