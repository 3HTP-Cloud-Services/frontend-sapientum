<script>
  import { push } from 'svelte-spa-router';
  import { onMount } from 'svelte';
  import Chat from './components/Chat.svelte';
  import { checkAuth, checkChatAccess } from './lib/auth.js';
  
  let messages = [];
  let userInput = '';
  
  onMount(async () => {
    console.log('EmbeddedChat component mounted');
    
    // Check if user has chat access
    const isAuth = await checkAuth();
    if (!isAuth) {
      push('/login');
      return;
    }
    
    const hasChatAccess = await checkChatAccess();
    if (!hasChatAccess) {
      console.log('User does not have chat access');
      push('/login');
    }
  });
</script>

<div class="chat-wrapper">
  <Chat 
    {messages}
    {userInput} 
    isEmbedded={true}
    showHeader={false}
    redirectPath="/login"
  />
</div>

<style>
  .chat-wrapper {
    height: calc(100vh - 60px);
    display: flex;
    flex-direction: column;
  }
</style>