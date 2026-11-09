/* Song metadata and private mashup upload use the same guest/organiser form. */
songForm=function(guest=false,id=null){
 const song=(state.songs||[]).find(s=>s.id===id)||{};let savedId=id;
 modal(guest?'Put your song on the list.':id?'A little tune-up.':'Add a song to the celebration.',`<form>${field('Song name','name','text',song.name||'')}<label>Artist (optional)<input name="artist" maxlength="100" value="${esc(song.artist||'')}"></label><label>Spotify song link (optional)<input name="spotifyUrl" type="url" maxlength="500" placeholder="https://open.spotify.com/track/…" value="${esc(song.spotifyUrl||'')}"></label><p class="subtitle">In Spotify, use Share → Copy song link. Leave it blank for a Spotify search link.</p><label>Upload your song mashup (optional)<input id="song-audio-file" type="file" accept=".mp3,.wav,.m4a,.ogg,.opus,audio/mpeg,audio/wav,audio/mp4,audio/ogg"></label><p class="subtitle">MP3, WAV, M4A or OGG · Up to 20 MB and 30 minutes. MP3 offers the widest phone compatibility. Guests can access their own requests; authorised organisers can play and download the audio.</p><label id="audio-consent-label" hidden><span><input type="checkbox" name="audioConsent"> I can share this audio file with the wedding organisers.</span></label>${song.audio?`<p>Current mashup: ${esc(song.audio.filename)}</p><label><span><input type="checkbox" name="removeAudio"> Remove current mashup (keeps the song request)</span></label>`:''}${guest?'':field('Requested by','owner','text',song.owner||state.user.name)}<p id="song-upload-status" role="status" aria-live="polite"></p>${formFooter(guest?'Send to the DJ list':'Save song')}</form>`);
 const form=$('#modal form'),fileInput=$('#song-audio-file'),status=$('#song-upload-status');
 fileInput.onchange=()=>{const file=fileInput.files[0];$('#audio-consent-label').hidden=!file;form.elements.audioConsent.required=Boolean(file);if(file&&form.elements.removeAudio)form.elements.removeAudio.checked=false;status.textContent=file?'Selected '+file.name:''};
 form.actionHandler=async values=>{
  const file=fileInput.files[0];if(file&&file.size>20*1024*1024)throw Error('Choose an audio file up to 20 MB.');
  const buttons=Array.from($('#modal').querySelectorAll('button'));buttons.forEach(b=>b.disabled=true);fileInput.disabled=true;let detailsSaved=false;
  try{
   status.textContent='Saving your song…';const details={name:values.name,artist:values.artist,spotifyUrl:values.spotifyUrl};
   const response=guest?await api('song',{...details,...(savedId?{id:savedId}:{})}):await api('save',{kind:'songs',item:{...song,...details,owner:values.owner,...(savedId?{id:savedId}:{})}});savedId=response.id;detailsSaved=true;
   if(file){
    status.textContent='Uploading your mashup. Keep this window open…';
    const data=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result.split(',')[1]);reader.onerror=()=>reject(Error('Could not read the audio file.'));reader.readAsDataURL(file)});
    await api('song-audio',{songId:savedId,filename:file.name,data,consent:values.audioConsent==='on'});
   }else if(values.removeAudio==='on')await api('song-audio/remove',{songId:savedId});
   $('#modal').close();await refresh({throwOnError:true});toast(file?'Mashup uploaded. Your song is ready for the DJ.':guest?'Song request sent.':'Song saved.');
  }catch(e){status.textContent=(detailsSaved?'Song details are saved. The audio change was not completed. ':'')+e.message+' You can retry here without creating a duplicate song.';throw e}
  finally{buttons.forEach(b=>b.disabled=false);fileInput.disabled=false}
 };
};
