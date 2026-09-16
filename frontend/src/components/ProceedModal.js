import React from "react";
import {
  Button,
  Dialog,
  DialogHeader,
  DialogBody,
  DialogFooter
} from "@material-tailwind/react";
import { useNavigate } from "react-router-dom";
 
export function ProceedModal({open,setOpen, video_id}) {
  const navigate = useNavigate();
  
  const HandleVideo = () => navigate(`/videos/${video_id}`);
  
  const handleOpen = () => setOpen(!open);
  if (!open){
    return <></>
  }
  return (
      <Dialog
        open={open}
        handler={handleOpen}
        animate={{
          mount: { scale: 1, y: 0 },
          unmount: { scale: 0.9, y: -100 },
        }}
      >
        <DialogHeader>Your video is ready !</DialogHeader>
        <DialogBody>
          Your video is ready ! You can now edit it or render it ! Do you want to go to the editing page ?
        </DialogBody>
        <DialogFooter>
          <Button
            variant="text"
            color="red"
            onClick={handleOpen}
            className="mr-1"
          >
            <span>Cancel</span>
          </Button>
          <Button variant="gradient" color="green" onClick={HandleVideo}>
            <span>Yes!</span>
          </Button>
        </DialogFooter>
      </Dialog>
  );
}