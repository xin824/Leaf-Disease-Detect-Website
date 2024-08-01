import './PlantCard.css'
import EditBox from './EditBox';
import { useEffect, useState } from 'react';

interface Plant {
    id: number;
    ip: string;
    name: string;
    state: string;
    image_path: string;
    update_time: string;
  }
  
  interface PlantCardProps {
    plant: Plant | undefined;
    updateCallback: () => void;
    wifiIp: string;
  }

function PlantCard({ plant, updateCallback, wifiIp}: PlantCardProps) {
    const [progressValue, setProgressValue] = useState(0);
    const [updateTime, setUpdateTime] = useState('Refresh to load last updated time');
    const [key, setKey] = useState(new Date());

    useEffect(() => {
        //if(plant)
        //    setProgressValue(parseInt(plant.update_time));
        var interval = setInterval(() => tick(), 1000);
	
	return () => clearInterval(interval);
    }, []);
    
    function tick(){
        setKey(new Date());
        console.log(new Date().getSeconds().toString());
    }

    async function fetchImageLastModified(imageName: string): Promise<string | null> {
        try {
            const response = await fetch(`${wifiIp}/update_time/${encodeURIComponent(imageName)}`);
            if (response.ok) {
                const data = await response.json();
                return data.lastModified;
            } else {
                throw new Error('Failed to fetch image last modified time');
            }
        } catch (error) {
            console.error('Error fetching image last modified time:', error);
            return null;
        }
    }

    // Example usage
    const imageName = `${plant?.ip}.jpg`; // Replace with your image path
    fetchImageLastModified(imageName)
        .then(lastModified => {
            if (lastModified) {
                // console.log('Image last modified:', lastModified);
                setUpdateTime(lastModified);
            } else {
                console.log('Image last modified not available');
            }
        });

  return (
    // <div className="container-fluid" style={{backgroundColor: "#405F43", height: '100vh'}}>
        <div className="d-flex container-xl justify-content-center align-items-center">
            <div className="card m-5 p-md-4 p-5">
                <div className="row g-0">
                    <div className="col-md-4 d-flex justify-content-center align-items-center">
                        <img src={`./image/${plant?.ip}/${new Date().getSeconds().toString()}.jpg`} className="img-fluid plantPicture" alt="plant picture"/>
                        {/* <img src={`../../image/${plant?.ip}.jpg`} className="img-fluid plantPicture" alt="plant picture"/> */}
                    </div>
                    <div className="col-md-8 p-2">
                        <div className="card-body">
                            <EditBox plant={plant} updateCallback={updateCallback} wifiIp = {wifiIp}></EditBox>
                            <div className='PlantState'>{plant?.state}</div>
                            <div className="progress progress-cus2" role="progressbar" aria-label="progressbar" 
                                aria-valuenow={progressValue} aria-valuemin={0} aria-valuemax={100}>
                                <div className="progress-bar" style={{ width: `50%`, backgroundColor: '#92BA96', borderRadius: '50px'}}></div>
                            </div>
                            <p className="card-text">
                                <small className="font-time justify-content-end d-flex">Last updated: {plant?.update_time}</small>
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    // </div>
  );
}

export default PlantCard;
