import { axiosPrivateInstance } from "./axiosPrivate"; 
import { useAxiosPrivate } from "../hooks/useAxiosPrivate";

export const generateVideo = async (data) => {

    try{
        const response = await axiosPrivateInstance.post('generate/', data);
      
        return response.data

    }catch (error){
        console.error('Error fetching data:', error);

    }
    
}

export const generateTwitchVideo = async (data) => {
    try{
        const response = await axiosPrivateInstance.post('twitch_generate/', data);
      
        return response.data

    }catch (error){
        console.error('Error fetching data:', error);

    }
}


export const getVoices = async () => {
    try {

        var url = "voices/"
      
        const response = await axiosPrivateInstance.get(url); // replace with your endpoint
        return response.data;
    } catch (error) {
        console.error('Error fetching data:', error);
        
    }
};


export const createAvatar = async (data) => {
    try{
        const response = await axiosPrivateInstance.post('avatars/', data);
        return response.data


    }catch (error){
        console.error('Error fetching data:', error);

    }

}


export const getAvatars = async (name) => {
    try {

        var url = "avatars/"
        if (name){
            url = url+"?search=" +name
        }

        const response = await axiosPrivateInstance.get(url); // replace with your endpoint
        return response.data;
    } catch (error) {
        console.error('Error fetching data:', error);
        
    }
};


export const deleteAvatar = async (id) =>  {
    try {

        var url = "avatars/" + id +"/"
      
        const response = await axiosPrivateInstance.delete(url); // replace with your endpoint
        return response.data;
    } catch (error) {
        console.error('Error fetching data:', error);
        
    }
};

export const getVideos = async (search, page) => {
    try {

        var url = "video/?"
        if (search){
            url = url+"search=" +search
        }
        if (page){
            url = url+"&page=" +page
        }


        const response = await axiosPrivateInstance.get(url); // replace with your endpoint
        return response.data;
    } catch (error) {
        console.error('Error fetching data:', error);
        
    }
};

export const deleteVideo = async (id) =>  {
    try {

        var url = "video/" + id +"/"
      
        const response = await axiosPrivateInstance.delete(url); // replace with your endpoint
        return response.data;
    } catch (error) {
        console.error('Error fetching data:', error);
        
    }
};

export const renderVideo = async (id) => {
    try {
        var url = "video/" + id +"/render_video/"
      
        const response = await axiosPrivateInstance.patch(url); // replace with your endpoint
        return response.data;
    } catch (error) {
        console.error('Error fetching data:', error);
        
    }
}


export const getVideo = async (id) =>  {
    try {

        var url = "video/" + id +"/"
      
        const response = await axiosPrivateInstance.get(url); // replace with your endpoint
        return response.data;
    } catch (error) {
        console.error('Error fetching data:', error);
        
    }
};

export const deleteImageScene = async (id) =>  {
    try {

        var url = "scene_image/" + id +"/"
      
        const response = await axiosPrivateInstance.delete(url); // replace with your endpoint
        return response.data;
    } catch (error) {
        console.error('Error fetching data:', error);
        
    }
};


export const getIntro = async (search = null) => {
    try {

        var url = "intro/"

        if(search){
            url += "?search="+ search
        }
      
        const response = await axiosPrivateInstance.get(url); 
        return response.data;
    } catch (error) {
        console.error('Error fetching data:', error);
        
    }
};



export const getOutro = async (search = null) => {
    try {

        var url = "outro/"

        if(search){
            url += "?search="+ search
        }
      
        const response = await axiosPrivateInstance.get(url); 
        return response.data;
    } catch (error) {
        console.error('Error fetching data:', error);
        
    }
};


export const updateVideo = async (id,data) => {
    try{
        var url = "video/" + id +"/"
        const response = await axiosPrivateInstance.patch(url, data);
      
        return response.data

    }catch (error){
        console.error('Error fetching data:', error);

    }
}


export const updateScene = async (id, data) => {

    try{
        var url = "scene/" + id +"/"
        const response = await axiosPrivateInstance.patch(url, data);
      
        return response.data

    }catch (error){
        console.error('Error fetching data:', error);

    }
    
}



export const generateScene = async (id, data) => {

    try{
        var url = "scene/" + id +"/generate/"
        const response = await axiosPrivateInstance.patch(url, data);
      
        return response.data

    }catch (error){
        console.error('Error fetching data:', error);

    }
}



export const updateSceneImage = async (id,scene_image_id, data) => {

    try{
        var url = "scene/" + id +"/change_image_scene/"
        if (scene_image_id){
            url = url + "?scene_image=" + scene_image_id;

        }
        const response = await axiosPrivateInstance.post(url, data);
      
        return response.data

    }catch (error){
        console.error('Error fetching data:', error);

    }
    
}


export const generateSceneImage = async (id, data) => {

    try{
        var url = "scene/" + id +"/generate_image_scene/"
     
        const response = await axiosPrivateInstance.post(url, data);
      
        return response.data

    }catch (error){
        console.error('Error fetching data:', error);

    }
}



export const createScene = async (id, data) => {

    try{
        var url = "video/" + id +"/add_scene/"
     
        const response = await axiosPrivateInstance.post(url, data);
      
        return response.data

    }catch (error){
        console.error('Error fetching data:', error);

    }
}

export const createIntro = async (data) => {

    try{
        var url = "intro/"
     
        const response = await axiosPrivateInstance.post(url, data);
      
        return response.data

    }catch (error){
        console.error('Error fetching data:', error);

    }
}

export const createOutro = async (data) => {

    try{
        var url = "outro/"
     
        const response = await axiosPrivateInstance.post(url, data);
      
        return response.data

    }catch (error){
        console.error('Error fetching data:', error);

    }
}


export const deleteIntro = async (id) => {

    try{
        var url = "intro/"+id+"/"
     
        const response = await axiosPrivateInstance.delete(url);
      
        return response.data

    }catch (error){
        console.error('Error fetching data:', error);

    }
}

export const deleteOutro = async (id) => {

    try{
        var url = "outro/"+id+"/"
     
        const response = await axiosPrivateInstance.delete(url);
      
        return response.data

    }catch (error){
        console.error('Error fetching data:', error);

    }
}


export const logout = async () => {

    try{
        var url = "logout/"
     
        const response = await axiosPrivateInstance.post(url);
      
        return response

    }catch (error){
        console.error('Error fetching data:', error);

    }
}