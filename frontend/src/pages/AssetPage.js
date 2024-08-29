import React, { useEffect, useState } from "react";
import { getIntro, getOutro } from "../api/apiService";
import { SearchInput } from "../components/ui/SearchInput";
import { SmallTable } from "../components/SmallTable";
import { AssetCreationModal } from "../components/AssetCreationModal";
import { createIntro, createOutro } from "../api/apiService";
import { DeleteModal } from "../components/DeleteModal";
import { deleteIntro, deleteOutro } from "../api/apiService";

export const AssetPage = () => {
  const [intros, setIntros] = useState([]);
  const [outros, setOutros] = useState([]);
  const [showIntroModal, setShowIntroModal] = useState(false);
  const [showOutroModal, setShowOutroModal] = useState(false);
  


  useEffect(() => {
    getIntro().then((response) => {
      setIntros(response);
    });
    getOutro().then((response) => {
      setOutros(response);
    });
  }, []);

  return (
    <>
      <AssetCreationModal
        showModal={showIntroModal}
        setShowModal={setShowIntroModal}
        nameh1="Intro"
        ApiCall={createIntro}
        setItems={setIntros}
      />
      <AssetCreationModal
        showModal={showOutroModal}
        setShowModal={setShowOutroModal}
        nameh1="Outro"
        ApiCall={createOutro}
        setItems={setOutros}


      />

      <div className="p-4">
        <div className="grid grid-cols-2 gap-4">
          {/* Intros Table */}
          <div>
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold">Intros</h2>
              <div className="flex items-center space-x-2">
              <button onClick={(e) => {setShowIntroModal(true)}} className="bg-blue-500 text-white px-4 py-2 rounded-lg hover:bg-blue-600">
              Create
                </button>
                <SearchInput placeholder="Search Intros" />
              </div>
            </div>
            <div className="overflow-x-auto">
              <SmallTable data={intros} setData={setIntros} deleteFunction={deleteIntro} />
            </div>
          </div>

          {/* Outros Table */}
          <div>
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold">Outros</h2>
              <div className="flex items-center space-x-2">
                <button onClick={(e) => {setShowOutroModal(true)}} className="bg-blue-500 text-white px-4 py-2 rounded-lg hover:bg-blue-600">
                  Create
                </button>
                <SearchInput placeholder="Search Outros" />
              </div>
            </div>
            <div className="overflow-x-auto">
              <SmallTable data={outros} setData={setOutros} deleteFunction={deleteOutro}/>
            </div>
          </div>
        </div>
      </div>
    </>
  );
};
